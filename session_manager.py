import os
import uuid
import tempfile
import traceback
from typing import Optional, Dict, Any
import smlibpy
from smlibpy import *

TEMP_DIR = os.path.join(tempfile.gettempdir(), "smlib_web_studio")
os.makedirs(TEMP_DIR, exist_ok=True)

class SessionManager:
    """管理 CAD 模型会话状态与临时文件导出"""

    def __init__(self):
        self.part = None
        self.script = "from smlibpy import *\n"
        self.name = "model"
        self.stats = {"volume": 0.0, "compute_ms": 0.0}

    def set_model(self, part, script: str, name: str, compute_ms: float = 0.0):
        self.part = part
        self.script = script
        self.name = name
        self.stats = {
            "volume": round(getattr(part, "volume", 0), 2) if part else 0.0,
            "compute_ms": round(compute_ms, 2)
        }

    def get_current(self) -> Dict[str, Any]:
        return {
            "part": self.part,
            "script": self.script,
            "name": self.name,
            "stats": self.stats
        }

    def export_gltf(self, part=None, name="model") -> str:
        target = part if part is not None else self.part
        if target is None:
            raise ValueError("没有可导出的几何模型")

        gltf_path = os.path.join(TEMP_DIR, f"{name}_{uuid.uuid4().hex[:8]}.gltf")
        try:
            target.export(gltf_path)
            with open(gltf_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            traceback.print_exc()
            raise ValueError(f"三维网格导出失败: {str(e)}")
        finally:
            try:
                if os.path.exists(gltf_path):
                    os.remove(gltf_path)
            except Exception:
                pass

    def export_file(self, fmt: str) -> tuple[bytes, str, str]:
        """导出为指定格式字节流，返回: (bytes, mime_type, filename)"""
        fmt = fmt.lower()
        part = self.part
        name = self.name or "model"

        if fmt == "py":
            script_bytes = (self.script or "from smlibpy import *\n").encode("utf-8")
            return script_bytes, "text/x-python", f"{name}.py"

        if part is None:
            raise ValueError("当前没有可导出的实体模型")

        out_path = os.path.join(TEMP_DIR, f"{name}_{uuid.uuid4().hex[:6]}.{fmt}")
        try:
            if fmt in ["step", "stp"]:
                part.export(out_path)
                mime = "application/step"
                dl_name = f"{name}.step"
            elif fmt == "stl":
                part.export(out_path)
                mime = "model/stl"
                dl_name = f"{name}.stl"
            elif fmt == "gltf":
                part.export(out_path)
                mime = "model/gltf+json"
                dl_name = f"{name}.gltf"
            else:
                raise ValueError(f"不支持的格式: {fmt}")

            with open(out_path, "rb") as f:
                data = f.read()
            return data, mime, dl_name
        finally:
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except Exception:
                pass

session_manager = SessionManager()
