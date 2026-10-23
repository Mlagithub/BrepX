import os
import sys
import time
import json
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
from semantic_manager import semantic_manager
from session_manager import session_manager

app = FastAPI(title="SMLib Studio Next", description="AI+CAD+CAE 工业流体几何工作台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 1. 参数定义与内置模板 ---
class ParametricRequest(BaseModel):
    template: str
    params: Dict[str, Any]


def build_parametric_part(template: str, params: Dict[str, Any]):
    """预设参数化模板生成器"""
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
            f"part = Box({length}, {width}, {thickness})"
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
            for dx in [-bolt_offset_x, bolt_offset_x]:
                for dy in [-bolt_offset_y, bolt_offset_y]:
                    part = part - Cylinder(bolt_hole_r, thickness + 4).translate(dx, dy, 0)
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

        base = Box(length, width, height)
        cut_out = Box(length - thickness + 2, width + 2, height - thickness + 2).translate(thickness / 2 + 1, 0, thickness / 2 + 1)
        part = base - cut_out
        script_lines = [
            "from smlibpy import *",
            f"base = Box({length}, {width}, {height})",
            f"cut_out = Box({length - thickness + 2}, {width + 2}, {height - thickness + 2}).translate({thickness / 2 + 1}, 0, {thickness / 2 + 1})",
            "part = base - cut_out"
        ]

        if fillet_r > 0:
            try:
                part = part.fillet(part.edges().parallel_to(Y), fillet_r)
                script_lines.append(f"part = part.fillet(part.edges().parallel_to(Y), {fillet_r})")
            except Exception: pass

        if hole_r > 0:
            part = part - Cylinder(hole_r, thickness + 4).translate(length / 2 - 15, 0, -height / 2 + thickness / 2)
            script_lines.append(f"part = part - Cylinder({hole_r}, {thickness + 4}).translate({length / 2 - 15}, 0, {-height / 2 + thickness / 2})")

        return part, "\n".join(script_lines)

    elif template == "bushing":
        od = float(params.get("od", 40))
        id_inner = float(params.get("id", 20))
        length = float(params.get("length", 60))
        flange_od = float(params.get("flange_od", 60))
        flange_len = float(params.get("flange_len", 12))

        body = Cylinder(od / 2, length)
        flange = Cylinder(flange_od / 2, flange_len).translate(0, 0, length / 2 - flange_len / 2)
        bore = Cylinder(id_inner / 2, length + 4)
        part = (body + flange) - bore
        script = f"from smlibpy import *\nbody = Cylinder({od / 2}, {length})\nflange = Cylinder({flange_od / 2}, {flange_len}).translate(0, 0, {length / 2 - flange_len / 2})\nbore = Cylinder({id_inner / 2}, {length + 4})\npart = (body + flange) - bore"
        return part, script

    elif template == "csg_demo":
        box_size = float(params.get("box_size", 50))
        sphere_r = float(params.get("sphere_r", 32))
        cyl_r = float(params.get("cyl_r", 18))

        box = Box(box_size, box_size, box_size)
        sphere = Sphere(sphere_r)
        core = box & sphere
        cyl_z = Cylinder(cyl_r, box_size + 4)
        cyl_x = Cylinder(cyl_r, box_size + 4).rotate(Y, 90)
        cyl_y = Cylinder(cyl_r, box_size + 4).rotate(X, 90)
        part = core - (cyl_z + cyl_x + cyl_y)
        script = f"from smlibpy import *\nbox = Box({box_size}, {box_size}, {box_size})\nsphere = Sphere({sphere_r})\ncore = box & sphere\ncyl_z = Cylinder({cyl_r}, {box_size + 4})\ncyl_x = Cylinder({cyl_r}, {box_size + 4}).rotate(Y, 90)\ncyl_y = Cylinder({cyl_r}, {box_size + 4}).rotate(X, 90)\npart = core - (cyl_z + cyl_x + cyl_y)"
        return part, script

    else:
        raise ValueError(f"未知模板: {template}")


# --- 2. 核心 API 路由 ---

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
        compute_ms = (time.perf_counter() - t0) * 1000
        session_manager.set_model(part, script, req.template, compute_ms)
        gltf_data = session_manager.export_gltf(part, req.template)

        return {
            "ok": True,
            "gltf": gltf_data,
            "script": script,
            "stats": session_manager.stats,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


class ScriptRequest(BaseModel):
    script: str
    name: Optional[str] = "custom_part"


@app.post("/api/build/script")
def api_build_script(req: ScriptRequest):
    t0 = time.perf_counter()
    user_globals = {"__name__": "__main__", "smlibpy": smlibpy}
    for attr in dir(smlibpy):
        if not attr.startswith("__"):
            user_globals[attr] = getattr(smlibpy, attr)

    try:
        exec(req.script, user_globals)
        part = user_globals.get("part")
        if part is None:
            for v in user_globals.values():
                if hasattr(v, "volume") and hasattr(v, "export"):
                    part = v
                    break

        if part is None:
            raise ValueError("脚本未生成有效模型。请确保将最终模型赋值给 `part` 变量。")

        compute_ms = (time.perf_counter() - t0) * 1000
        session_manager.set_model(part, req.script, req.name or "custom", compute_ms)
        gltf_data = session_manager.export_gltf(part, req.name or "custom")

        return {
            "ok": True,
            "gltf": gltf_data,
            "script": req.script,
            "stats": session_manager.stats,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{type(e).__name__}: {str(e)}")


class ToolExecuteRequest(BaseModel):
    tool: str
    params: Optional[Dict[str, Any]] = {}
    base_on_current: Optional[bool] = False


@app.post("/api/tools/execute")
def api_tools_execute(req: ToolExecuteRequest):
    t0 = time.perf_counter()
    try:
        cur_part = session_manager.part if req.base_on_current else None
        cur_script = session_manager.script if req.base_on_current else ""

        part, script, explanation = execute_right_tool(req.tool, req.params, cur_part, cur_script)
        compute_ms = (time.perf_counter() - t0) * 1000

        session_manager.set_model(part, script, req.tool, compute_ms)
        gltf_data = session_manager.export_gltf(part, req.tool)

        return {
            "ok": True,
            "explanation": explanation,
            "code": script,
            "gltf": gltf_data,
            "stats": session_manager.stats,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


class TransformRequest(BaseModel):
    kind: str  # 'translate' | 'rotate' | 'scale'
    dx: Optional[float] = 0.0
    dy: Optional[float] = 0.0
    dz: Optional[float] = 0.0
    axis: Optional[str] = "Z"
    angle: Optional[float] = 0.0
    factor: Optional[float] = 1.0


@app.post("/api/transform")
def api_transform(req: TransformRequest):
    part = session_manager.part
    if part is None:
        raise HTTPException(status_code=400, detail="当前场景暂无可用模型，无法执行几何变换。")

    t0 = time.perf_counter()
    script = session_manager.script
    explanation = ""

    try:
        if req.kind == "translate":
            part = part.translate(req.dx, req.dy, req.dz)
            code_line = f"part = part.translate({req.dx}, {req.dy}, {req.dz})"
            explanation = f"已平移位移: ({req.dx}, {req.dy}, {req.dz}) mm"
        elif req.kind == "rotate":
            axis_obj = Z if req.axis.upper() == "Z" else Y if req.axis.upper() == "Y" else X
            part = part.rotate(axis_obj, req.angle)
            code_line = f"part = part.rotate({req.axis.upper()}, {req.angle})"
            explanation = f"已绕 {req.axis.upper()} 轴旋转 {req.angle}°"
        elif req.kind == "scale":
            if req.factor <= 0: raise HTTPException(status_code=400, detail="缩放因子必须大于 0")
            part = part.scale(req.factor)
            code_line = f"part = part.scale({req.factor})"
            explanation = f"已等比缩放 {req.factor} 倍"
        else:
            raise HTTPException(status_code=400, detail=f"未知的几何变换: {req.kind}")

        new_script = script.rstrip() + f"\n# 几何变换\n{code_line}\n"
        compute_ms = (time.perf_counter() - t0) * 1000
        session_manager.set_model(part, new_script, "transformed", compute_ms)
        gltf_data = session_manager.export_gltf(part, "transformed")

        return {
            "ok": True,
            "explanation": explanation,
            "code": new_script,
            "gltf": gltf_data,
            "stats": session_manager.stats,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/model/topology")
def api_model_topology():
    part = session_manager.part
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


# --- 3. Agent 与物理语义 ---

class AgentChatRequest(BaseModel):
    prompt: str
    history: Optional[List[Dict[str, Any]]] = []
    config: Optional[Dict[str, Any]] = {}


@app.post("/api/agent/chat")
def api_agent_chat(req: AgentChatRequest):
    t0 = time.perf_counter()
    res = cad_agent.chat(req.prompt, req.history, req.config)
    compute_ms = (time.perf_counter() - t0) * 1000

    part = res.get("part")
    gltf_data = None
    export_err = None
    if part is not None:
        try:
            session_manager.set_model(part, res.get("code", ""), "ai_model", compute_ms)
            gltf_data = session_manager.export_gltf(part, "ai_model")
        except Exception as e:
            export_err = str(e)
            part = None

    return {
        "ok": part is not None,
        "reply": res.get("explanation", ""),
        "code": res.get("code", ""),
        "gltf": gltf_data,
        "stats": session_manager.stats if part is not None else {"volume": 0, "compute_ms": compute_ms},
        "error": export_err or res.get("error")
    }


@app.post("/api/agent/test_llm")
def api_agent_test_llm(req: Dict[str, Any]):
    return cad_agent.test_connection(req)


class SemanticPatchRequest(BaseModel):
    face_index: int
    semantic_type: str
    name: Optional[str] = None
    normal: Optional[List[float]] = None
    area: Optional[float] = 0.0


@app.post("/api/semantic/patch")
def api_set_semantic_patch(req: SemanticPatchRequest):
    patch = semantic_manager.set_patch(
        face_index=req.face_index,
        semantic_type=req.semantic_type,
        name=req.name,
        normal=req.normal,
        area=req.area
    )
    return {"ok": True, "patch": patch, "all_patches": semantic_manager.get_all_patches()}


@app.get("/api/semantic/patches")
def api_get_semantic_patches():
    return {"ok": True, "patches": semantic_manager.get_all_patches()}


@app.delete("/api/semantic/patch/{patch_id}")
def api_delete_semantic_patch(patch_id: str):
    ok = semantic_manager.remove_patch(patch_id)
    return {"ok": ok, "all_patches": semantic_manager.get_all_patches()}


@app.get("/api/export/cfd_meta")
def api_export_cfd_meta():
    meta = semantic_manager.export_cfd_metadata()
    return Response(
        content=json.dumps(meta, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="cfd_boundaries.json"'}
    )


@app.get("/api/export/{fmt}")
def api_export(fmt: str):
    try:
        data, mime, filename = session_manager.export_file(fmt)
        return Response(
            content=data,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


# 静态前端资源挂载
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8080, reload=False)
