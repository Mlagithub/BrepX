import os
import sys
import time
import uuid
import tempfile
import traceback
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import smlibpy
from smlibpy import *
from agent import cad_agent
from tools_handler import execute_right_tool

app = FastAPI(title="SMLib Web Studio", description="smlibpy x cax-viewer integration")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for current active model
CURRENT_MODEL = {
    "part": None,
    "script": "",
    "name": "model",
    "stats": {},
}

TEMP_DIR = os.path.join(tempfile.gettempdir(), "smlib_web_studio")
os.makedirs(TEMP_DIR, exist_ok=True)


class ParametricRequest(BaseModel):
    template: str
    params: Dict[str, Any]


class ScriptRequest(BaseModel):
    script: str
    name: Optional[str] = "custom_part"


def build_parametric_part(template: str, params: Dict[str, Any]):
    """Generate part and Python script based on template and params."""
    if template == "flange":
        length = float(params.get("length", 100))
        width = float(params.get("width", 80))
        thickness = float(params.get("thickness", 12))
        fillet_r = float(params.get("fillet_r", 10))
        center_hole_r = float(params.get("center_hole_r", 15))
        bolt_holes = bool(params.get("bolt_holes", True))
        bolt_hole_r = float(params.get("bolt_hole_r", 4))
        bolt_offset_x = float(params.get("bolt_offset_x", 35))
        bolt_offset_y = float(params.get("bolt_offset_y", 25))

        script_lines = [
            "from smlibpy import *",
            f"part = Box({length}, {width}, {thickness})",
        ]
        part = Box(length, width, thickness)

        if fillet_r > 0:
            part = part.fillet(part.edges().parallel_to(Z), fillet_r)
            script_lines.append(f"part = part.fillet(part.edges().parallel_to(Z), {fillet_r})")

        if center_hole_r > 0:
            chole = Cylinder(center_hole_r, thickness + 4)
            part = part - chole
            script_lines.append(f"part = part - Cylinder({center_hole_r}, {thickness + 4})")

        if bolt_holes and bolt_hole_r > 0:
            bolt_script_parts = []
            for dx in [-bolt_offset_x, bolt_offset_x]:
                for dy in [-bolt_offset_y, bolt_offset_y]:
                    b_hole = Cylinder(bolt_hole_r, thickness + 4).translate(dx, dy, 0)
                    part = part - b_hole
            script_lines.append(f"# 4 corner mounting holes")
            script_lines.append(f"for dx in [-{bolt_offset_x}, {bolt_offset_x}]:")
            script_lines.append(f"    for dy in [-{bolt_offset_y}, {bolt_offset_y}]:")
            script_lines.append(f"        part = part - Cylinder({bolt_hole_r}, {thickness + 4}).translate(dx, dy, 0)")

        return part, "\n".join(script_lines)

    elif template == "bracket":
        length = float(params.get("length", 80))
        width = float(params.get("width", 50))
        height = float(params.get("height", 60))
        thickness = float(params.get("thickness", 10))
        fillet_r = float(params.get("fillet_r", 6))
        hole_r = float(params.get("hole_r", 6))

        # Base block - cut out the corner to make L-bracket
        script_lines = [
            "from smlibpy import *",
            f"base = Box({length}, {width}, {height})",
            f"cut_out = Box({length - thickness + 2}, {width + 2}, {height - thickness + 2}).translate({thickness / 2 + 1}, 0, {thickness / 2 + 1})",
            f"part = base - cut_out"
        ]
        base = Box(length, width, height)
        cut_out = Box(length - thickness + 2, width + 2, height - thickness + 2).translate(thickness / 2 + 1, 0, thickness / 2 + 1)
        part = base - cut_out

        if fillet_r > 0:
            try:
                part = part.fillet(part.edges().parallel_to(Y), fillet_r)
                script_lines.append(f"part = part.fillet(part.edges().parallel_to(Y), {fillet_r})")
            except Exception:
                pass

        if hole_r > 0:
            h1 = Cylinder(hole_r, thickness + 4).translate(length / 2 - 15, 0, -height / 2 + thickness / 2)
            part = part - h1
            script_lines.append(f"part = part - Cylinder({hole_r}, {thickness + 4}).translate({length / 2 - 15}, 0, {-height / 2 + thickness / 2})")

        return part, "\n".join(script_lines)

    elif template == "bushing":
        od = float(params.get("od", 40))
        id_inner = float(params.get("id", 20))
        length = float(params.get("length", 60))
        flange_od = float(params.get("flange_od", 60))
        flange_len = float(params.get("flange_len", 12))

        script_lines = [
            "from smlibpy import *",
            f"body = Cylinder({od / 2}, {length})",
            f"flange = Cylinder({flange_od / 2}, {flange_len}).translate(0, 0, {length / 2 - flange_len / 2})",
            f"bore = Cylinder({id_inner / 2}, {length + 4})",
            f"part = (body + flange) - bore"
        ]
        body = Cylinder(od / 2, length)
        flange = Cylinder(flange_od / 2, flange_len).translate(0, 0, length / 2 - flange_len / 2)
        bore = Cylinder(id_inner / 2, length + 4)
        part = (body + flange) - bore

        return part, "\n".join(script_lines)

    elif template == "csg_demo":
        box_size = float(params.get("box_size", 50))
        sphere_r = float(params.get("sphere_r", 32))
        cyl_r = float(params.get("cyl_r", 18))

        script_lines = [
            "from smlibpy import *",
            f"# Intersection of box and sphere, with 3 orthogonal boreholes",
            f"box = Box({box_size}, {box_size}, {box_size})",
            f"sphere = Sphere({sphere_r})",
            f"core = box & sphere",
            f"cyl_z = Cylinder({cyl_r}, {box_size + 4})",
            f"cyl_x = Cylinder({cyl_r}, {box_size + 4}).rotate(Y, 90)",
            f"cyl_y = Cylinder({cyl_r}, {box_size + 4}).rotate(X, 90)",
            f"part = core - (cyl_z + cyl_x + cyl_y)"
        ]
        box = Box(box_size, box_size, box_size)
        sphere = Sphere(sphere_r)
        core = box & sphere
        cyl_z = Cylinder(cyl_r, box_size + 4)
        cyl_x = Cylinder(cyl_r, box_size + 4).rotate(Y, 90)
        cyl_y = Cylinder(cyl_r, box_size + 4).rotate(X, 90)
        part = core - (cyl_z + cyl_x + cyl_y)

        return part, "\n".join(script_lines)

    else:
        raise ValueError(f"Unknown template: {template}")


def export_part_to_gltf(part, name="model"):
    """Export part to glTF string."""
    gltf_path = os.path.join(TEMP_DIR, f"{name}_{uuid.uuid4().hex[:8]}.gltf")
    try:
        part.export(gltf_path)
        with open(gltf_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        traceback.print_exc()
        raise ValueError(f"三维几何网格三角化或导出失败: {str(e)}。请检查模型尺寸是否重合或退化。")
    finally:
        try:
            if os.path.exists(gltf_path):
                os.remove(gltf_path)
        except Exception:
            pass


@app.get("/api/info")
def get_info():
    return {
        "status": "ready",
        "smlibpy_version": getattr(smlibpy, "__version__", "0.4.0"),
        "kernel": "SMLib NURBS Kernel (C++ / OpenNURBS / USD-BRep)",
        "platform": sys.platform,
        "python_version": sys.version,
    }


@app.post("/api/build/parametric")
def api_build_parametric(req: ParametricRequest):
    t0 = time.perf_counter()
    try:
        part, script = build_parametric_part(req.template, req.params)
        compute_ms = round((time.perf_counter() - t0) * 1000, 2)
        gltf_data = export_part_to_gltf(part, req.template)

        # Update cache
        CURRENT_MODEL["part"] = part
        CURRENT_MODEL["script"] = script
        CURRENT_MODEL["name"] = req.template
        CURRENT_MODEL["stats"] = {
            "volume": round(getattr(part, "volume", 0), 2),
            "compute_ms": compute_ms,
        }

        return {
            "ok": True,
            "gltf": gltf_data,
            "script": script,
            "stats": CURRENT_MODEL["stats"],
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/build/script")
def api_build_script(req: ScriptRequest):
    t0 = time.perf_counter()
    user_globals = {
        "__name__": "__main__",
        "smlibpy": smlibpy,
    }
    # Expose all smlibpy symbols
    for attr in dir(smlibpy):
        if not attr.startswith("__"):
            user_globals[attr] = getattr(smlibpy, attr)

    try:
        exec(req.script, user_globals)
        part = user_globals.get("part")
        if part is None:
            # Try to find any Part or Shape instance in globals
            for k, v in user_globals.items():
                if hasattr(v, "volume") and hasattr(v, "export"):
                    part = v
                    break

        if part is None:
            raise ValueError("脚本未生成有效模型。请确保将最终模型赋值给 `part` 变量，例如：`part = Box(50, 40, 10)`")

        compute_ms = round((time.perf_counter() - t0) * 1000, 2)
        gltf_data = export_part_to_gltf(part, req.name or "custom")

        CURRENT_MODEL["part"] = part
        CURRENT_MODEL["script"] = req.script
        CURRENT_MODEL["name"] = req.name or "custom"
        CURRENT_MODEL["stats"] = {
            "volume": round(getattr(part, "volume", 0), 2),
            "compute_ms": compute_ms,
        }

        return {
            "ok": True,
            "gltf": gltf_data,
            "script": req.script,
            "stats": CURRENT_MODEL["stats"],
        }
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)


class AgentChatRequest(BaseModel):
    prompt: str
    history: Optional[List[Dict[str, Any]]] = []
    config: Optional[Dict[str, Any]] = {}


@app.post("/api/agent/chat")
def api_agent_chat(req: AgentChatRequest):
    t0 = time.perf_counter()
    res = cad_agent.chat(req.prompt, req.history, req.config)
    compute_ms = round((time.perf_counter() - t0) * 1000, 2)

    part = res.get("part")
    gltf_data = None
    export_err = None
    if part is not None:
        try:
            gltf_data = export_part_to_gltf(part, "ai_model")
            CURRENT_MODEL["part"] = part
            CURRENT_MODEL["script"] = res.get("code", "")
            CURRENT_MODEL["name"] = "ai_model"
            CURRENT_MODEL["stats"] = {
                "volume": round(getattr(part, "volume", 0), 2),
                "compute_ms": compute_ms,
            }
        except Exception as e:
            export_err = str(e)
            part = None

    return {
        "ok": part is not None,
        "reply": res.get("explanation", ""),
        "code": res.get("code", ""),
        "gltf": gltf_data,
        "stats": CURRENT_MODEL["stats"] if part is not None else {"volume": 0, "compute_ms": compute_ms},
        "error": export_err or res.get("error")
    }


@app.post("/api/agent/test_llm")
def api_agent_test_llm(req: Dict[str, Any]):
    return cad_agent.test_connection(req)


class ToolExecuteRequest(BaseModel):
    tool: str
    params: Optional[Dict[str, Any]] = {}
    base_on_current: Optional[bool] = False


@app.post("/api/tools/execute")
def api_tools_execute(req: ToolExecuteRequest):
    t0 = time.perf_counter()
    try:
        current_part = CURRENT_MODEL.get("part") if req.base_on_current else None
        current_script = CURRENT_MODEL.get("script", "") if req.base_on_current else ""

        part, script, explanation = execute_right_tool(req.tool, req.params, current_part, current_script)
        compute_ms = round((time.perf_counter() - t0) * 1000, 2)

        gltf_data = export_part_to_gltf(part, req.tool)
        CURRENT_MODEL["part"] = part
        CURRENT_MODEL["script"] = script
        CURRENT_MODEL["name"] = req.tool
        CURRENT_MODEL["stats"] = {
            "volume": round(getattr(part, "volume", 0), 2),
            "compute_ms": compute_ms,
        }

        return {
            "ok": True,
            "explanation": explanation,
            "code": script,
            "gltf": gltf_data,
            "stats": CURRENT_MODEL["stats"],
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


class TransformRequest(BaseModel):
    kind: str  # 'translate' | 'rotate' | 'scale'
    dx: Optional[float] = 0.0
    dy: Optional[float] = 0.0
    dz: Optional[float] = 0.0
    axis: Optional[str] = "Z"  # "X", "Y", "Z"
    angle: Optional[float] = 0.0
    factor: Optional[float] = 1.0


@app.post("/api/transform")
def api_transform(req: TransformRequest):
    part = CURRENT_MODEL.get("part")
    if part is None:
        raise HTTPException(status_code=400, detail="当前场景暂无可用模型，无法执行几何变换。")

    t0 = time.perf_counter()
    script = CURRENT_MODEL.get("script", "from smlibpy import *\n")
    explanation = ""

    try:
        if req.kind == "translate":
            part = part.translate(req.dx, req.dy, req.dz)
            code_line = f"part = part.translate({req.dx}, {req.dy}, {req.dz})"
            explanation = f"已平移位移增量: ({req.dx}, {req.dy}, {req.dz}) mm"
        elif req.kind == "rotate":
            axis_obj = Z if req.axis.upper() == "Z" else Y if req.axis.upper() == "Y" else X
            part = part.rotate(axis_obj, req.angle)
            code_line = f"part = part.rotate({req.axis.upper()}, {req.angle})"
            explanation = f"已绕 {req.axis.upper()} 轴旋转 {req.angle}°"
        elif req.kind == "scale":
            if req.factor <= 0:
                raise HTTPException(status_code=400, detail="缩放因子必须大于 0")
            part = part.scale(req.factor)
            code_line = f"part = part.scale({req.factor})"
            explanation = f"已等比缩放 {req.factor} 倍"
        else:
            raise HTTPException(status_code=400, detail=f"未知的几何变换类型: {req.kind}")

        new_script = script.rstrip() + f"\n# 几何变换\n{code_line}\n"
        compute_ms = round((time.perf_counter() - t0) * 1000, 2)
        gltf_data = export_part_to_gltf(part, "transformed_part")

        CURRENT_MODEL["part"] = part
        CURRENT_MODEL["script"] = new_script
        CURRENT_MODEL["stats"] = {
            "volume": round(getattr(part, "volume", 0), 2),
            "compute_ms": compute_ms,
        }

        return {
            "ok": True,
            "explanation": explanation,
            "code": new_script,
            "gltf": gltf_data,
            "stats": CURRENT_MODEL["stats"],
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/model/topology")
def api_model_topology():
    part = CURRENT_MODEL.get("part")
    if part is None:
        return {"ok": False, "msg": "空场景"}

    try:
        bbox = part.bbox()
        pmin = bbox.min
        pmax = bbox.max
        size = [round(float(bbox.size[0]), 2), round(float(bbox.size[1]), 2), round(float(bbox.size[2]), 2)]
        faces_count = len(list(part.faces()))
        edges_count = len(list(part.edges()))
        vertices_count = len(list(part.vertices()))
        area = round(getattr(part, "area", 0), 2)
        volume = round(getattr(part, "volume", 0), 2)

        return {
            "ok": True,
            "size": size,
            "bounds": {"min": [round(float(pmin[0]), 2), round(float(pmin[1]), 2), round(float(pmin[2]), 2)],
                       "max": [round(float(pmax[0]), 2), round(float(pmax[1]), 2), round(float(pmax[2]), 2)]},
            "faces_count": faces_count,
            "edges_count": edges_count,
            "vertices_count": vertices_count,
            "area": area,
            "volume": volume
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/export/{fmt}")
def api_export(fmt: str):
    part = CURRENT_MODEL["part"]
    name = CURRENT_MODEL["name"] or "model"
    if part is None:
        raise HTTPException(status_code=400, detail="暂无可用几何模型，请先生成模型。")

    fmt = fmt.lower()
    if fmt == "py":
        script = CURRENT_MODEL["script"] or "from smlibpy import *\n"
        return Response(
            content=script,
            media_type="text/x-python",
            headers={"Content-Disposition": f'attachment; filename="{name}.py"'}
        )

    out_file = os.path.join(TEMP_DIR, f"{name}_{uuid.uuid4().hex[:6]}.{fmt}")
    try:
        if fmt == "step" or fmt == "stp":
            part.export(out_file)
            media_type = "application/step"
            dl_name = f"{name}.step"
        elif fmt == "stl":
            part.export(out_file)
            media_type = "model/stl"
            dl_name = f"{name}.stl"
        elif fmt == "gltf":
            part.export(out_file)
            media_type = "model/gltf+json"
            dl_name = f"{name}.gltf"
        else:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式: {fmt}")

        with open(out_file, "rb") as f:
            data = f.read()
        try:
            os.remove(out_file)
        except Exception:
            pass

        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{dl_name}"'}
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


# Mount static directory for frontend
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8080, reload=False)
