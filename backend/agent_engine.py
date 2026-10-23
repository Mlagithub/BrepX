"""Embodied CAD & CFD Agent Engine for SMLib Studio Next.

Shares the unified WorkspaceSession namespace, injects active B-Rep topological
selections (`part.faces()[j]`, `part.edges()[n]`) and `smlibpy.mcp.discovery`
API documentation into the reasoning loop, and supports self-correction retries.
"""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from smlibpy.mcp import discovery
from .operators import build_operator_code
from .workspace import WorkspaceSession, workspace_session

SYSTEM_PROMPT = """你是 SMLib Studio Next 的具身 CAD 与 CFD 几何建模工程师。
你与人类工程师共享同一个实时 3D 视口与持久化 Python 工作区 (`part` 是当前场景中的主几何体)。

【核心建模规则】
1. 环境中已默认导入 `from smlibpy import *`、`import math`、`import numpy as np`。
2. 当用户在视口中选中了拓扑面或特征边（会在上下文【当前视口选区】中给出，例如 `part.faces()[4]` 或 `part.edges()[2]`），你必须直接针对该选区编写精确的增量修改代码：
   - 在选中面上打孔：`part = part - Hole(radius, depth).on(part.faces()[j])`
   - 在选中面上拉伸凸台或切槽：`part = part + extrude(part.faces()[j], h)` 或 `part = part - extrude(part.faces()[j], -h)`
   - 对选中边倒圆角/倒角：`_edges = list(part.edges()); part = part.fillet([_edges[i] for i in [...] ], r)`
   - 对选中面开口抽壳：`_faces = list(part.faces()); part = part.shell(t, openings=[_faces[j]])`
   - 移除选中特征面愈合：`_faces = list(part.faces()); part = part.remove_faces([_faces[j]])`
3. 最终结果必须赋值给 `part` 变量。不要调用 `show()` 或 `export()`。
4. 请将 Python 代码包裹在 ```python ... ``` 代码块中，并在代码块外给出简明的工程与流体几何说明。
"""


def retrieve_api_context(prompt: str, limit: int = 5) -> str:
    """Query `smlibpy.mcp.discovery` for relevant SMLib API signatures and summaries."""
    words = re.findall(r"[A-Za-z_]{3,}", prompt)
    zh_map = {
        "圆角": "fillet", "倒角": "chamfer", "抽壳": "shell", "孔": "Hole CounterBoreHole",
        "拉伸": "extrude", "旋转": "revolve", "扫掠": "sweep Helix", "放样": "loft",
        "阵列": "GridLocations PolarLocations", "镜像": "mirror", "切分": "split section",
        "拔模": "draft", "去圆角": "remove_fillets", "填平": "remove_faces", "样条": "Spline",
    }
    for zh_k, en_v in zh_map.items():
        if zh_k in prompt:
            words.extend(en_v.split())
    if not words:
        return ""
    try:
        hits = discovery.search(words)[:limit]
        lines = ["【相关 smlibpy 原生 API 参考】"]
        for _, entry in hits:
            lines.append(f"- {entry.line}: {entry.summary}")
        return "\n".join(lines)
    except Exception:
        return ""


def _extract_num(text: str, keywords: list[str], default_val: float) -> float:
    for kw in keywords:
        m = re.search(kw + r"[:\s=为到]*([+-]?\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return default_val


class LocalEmbodiedResolver:
    """Selection-aware local CAD semantic engine for zero-latency offline execution."""

    @staticmethod
    def resolve(
        prompt: str,
        selections: list[str],
        has_existing_part: bool,
    ) -> tuple[str, str, bool]:
        p_low = prompt.lower()
        nums = [float(x) for x in re.findall(r"([+-]?\d+(?:\.\d+)?)", prompt)]
        ev = _extract_num

        # 1. Selection-driven commands when the user has picked faces or edges in the viewport
        if selections and has_existing_part:
            if any(k in p_low for k in ["圆角", "fillet", "倒圆"]):
                r = ev(prompt, ["r", "半径", "圆角"], nums[0] if nums else 4.0)
                code, lbl, rep = build_operator_code("fillet", {"radius": abs(r)}, selections, True)
                return f"已针对您在视口中选中的拓扑边执行 R{abs(r)} mm 倒圆角。", code, rep

            if any(k in p_low for k in ["倒角", "chamfer", "斜角"]):
                d = ev(prompt, ["d", "距离", "倒角"], nums[0] if nums else 3.0)
                code, lbl, rep = build_operator_code("chamfer", {"distance": abs(d)}, selections, True)
                return f"已针对您在视口中选中的拓扑边执行 {abs(d)} mm 等距倒角。", code, rep

            if any(k in p_low for k in ["抽壳", "shell", "掏空", "薄壁"]):
                t = ev(prompt, ["壁厚", "厚度", "厚"], nums[0] if nums else 2.0)
                code, lbl, rep = build_operator_code("shell", {"thickness": abs(t)}, selections, True)
                return f"已将您选中的拓扑面作为开口面，执行壁厚 {abs(t)} mm 薄壁抽壳。", code, rep

            if any(k in p_low for k in ["移除", "删除", "填平", "抹平", "愈合", "remove"]):
                if "圆角" in p_low:
                    code, lbl, rep = build_operator_code("remove_fillets", {}, selections, True)
                    return "已擦除选定的圆角曲面并恢复锐角棱边。", code, rep
                code, lbl, rep = build_operator_code("remove_faces", {}, selections, True)
                return "已移除选定的特征面并由内核自动延伸愈合。", code, rep

            if any(k in p_low for k in ["孔", "hole", "打孔", "钻孔"]):
                d_val = ev(prompt, ["直径", "孔径", "半径", "r"], nums[0] if nums else 10.0)
                r_val = d_val / 2.0 if ("直径" in p_low or "孔径" in p_low) else d_val
                depth = ev(prompt, ["深", "深度", "高"], 40.0)
                code, lbl, rep = build_operator_code("hole", {"radius": abs(r_val), "depth": abs(depth)}, selections, True)
                return f"已在您选中的拓扑面上垂直开设半径 R{abs(r_val)} mm 的孔。", code, rep

            if any(k in p_low for k in ["拉伸", "extrude", "凸台", "切槽", "挖槽", "长高"]):
                h_val = ev(prompt, ["高度", "高", "深", "深度", "距离"], nums[0] if nums else 15.0)
                if any(k in p_low for k in ["槽", "切", "挖", "减"]):
                    h_val = -abs(h_val)
                code, lbl, rep = build_operator_code("extrude", {"height": h_val}, selections, True)
                return f"已沿您选中的拓扑面法向执行 {h_val} mm 拉伸变换。", code, rep

        # 2. CFD Flow Domain Templates & Pre-processing
        if any(k in p_low for k in ["文丘里", "喷嘴", "渐缩", "喉部", "venturi", "nozzle"]):
            r_in = ev(prompt, ["入口", "大端", "外径"], 25.0)
            r_th = ev(prompt, ["喉部", "喉径", "小端"], 12.0)
            l_c = ev(prompt, ["收缩", "长度", "长"], 35.0)
            l_d = ev(prompt, ["扩散"], 45.0)
            code = (
                f"conv = Cone({r_in}, {r_th}, {l_c})\n"
                f"div = Cone({r_th}, {r_in}, {l_d}).translate(0, 0, {(l_c + l_d) / 2.0})\n"
                f"body = conv + div\n"
                f"bore = Cone({r_in - 3}, {r_th - 3}, {l_c + 2}) + Cone({r_th - 3}, {r_in - 3}, {l_d + 2}).translate(0, 0, {(l_c + l_d) / 2.0})\n"
                f"part = body - bore"
            )
            return f"已创建【CFD 文丘里喷嘴流道】：入口 R{r_in}mm，喉部 R{r_th}mm。", code, True

        if any(k in p_low for k in ["弯管", "弯头", "elbow", "90度管"]):
            r_p = ev(prompt, ["管径", "半径", "内径"], 12.0)
            r_b = ev(prompt, ["弯曲半径", "回转半径"], 35.0)
            code = (
                f"outer_sk = Circle({r_p}).on(Plane.XZ).translate({r_b}, 0, 0)\n"
                f"inner_sk = Circle({max(2.0, r_p - 2.5)}).on(Plane.XZ).translate({r_b}, 0, 0)\n"
                f"part = revolve(outer_sk, Z, 90) - revolve(inner_sk, Z, 92)"
            )
            return f"已创建【CFD 90° 流体圆弧弯管】：管径 R{r_p}mm，回转半径 R{r_b}mm。", code, True

        if any(k in p_low for k in ["流体域", "内流道", "空腔", "cavity"]):
            code, lbl, _ = build_operator_code("cavity_extraction", {}, selections, has_existing_part)
            return "已通过反向包络布尔差集提取内部水密流体域。", code, False

        if any(k in p_low for k in ["去圆角", "消除圆角", "remove_fillets"]):
            code, lbl, _ = build_operator_code("remove_fillets", {}, selections, has_existing_part)
            return "已执行 CFD 去特征化：自动识别并擦除圆角面，延伸恢复锐边。", code, False

        # 3. Incremental modifications on existing part
        if has_existing_part and any(k in p_low for k in ["再", "增加", "加个", "打个", "开个", "倒个", "把", "改成", "修改"]):
            if any(k in p_low for k in ["圆角", "fillet"]):
                r = ev(prompt, ["圆角", "r", "半径"], nums[0] if nums else 5.0)
                code, _, _ = build_operator_code("fillet", {"radius": abs(r)}, selections, True)
                return f"已在现有模型上施加 R{abs(r)} mm 圆角。", code, False
            if any(k in p_low for k in ["孔", "通孔", "打孔"]):
                d_val = ev(prompt, ["直径", "孔径", "孔"], nums[0] if nums else 16.0)
                r_val = d_val / 2.0 if ("直径" in p_low or "孔径" in p_low) else d_val
                code = f"part = part - Cylinder({abs(r_val)}, 120)"
                return f"已在现有模型上贯穿切削半径 R{abs(r_val)} mm 的通孔。", code, False

        # 4. Standard mechanical parts (Flange, Bracket, Bushing, Box, Cylinder, Sphere)
        if any(k in p_low for k in ["法兰", "flange", "圆盘"]):
            d_out = ev(prompt, ["外径", "直径"], 80.0)
            d_in = ev(prompt, ["内孔", "内径", "通孔"], 30.0)
            h = ev(prompt, ["厚度", "厚", "高"], 12.0)
            r_out, r_in = d_out / 2.0, min(d_in / 2.0, d_out * 0.35)
            pcd = round((r_out + r_in) / 2.0, 1)
            code = (
                f"part = Cylinder({r_out}, {h}) - Cylinder({r_in}, {h + 4})\n"
                f"for i in range(4):\n"
                f"    ang = i * (math.pi / 2.0)\n"
                f"    part = part - Cylinder(4.0, {h + 4}).translate({pcd} * math.cos(ang), {pcd} * math.sin(ang), 0)"
            )
            return f"已创建【圆形管道法兰】：外径 Ø{d_out}mm，内孔 Ø{d_in}mm，厚度 {h}mm。", code, True

        if any(k in p_low for k in ["支架", "角码", "l型", "bracket"]):
            l = ev(prompt, ["长", "长度"], 80.0)
            w = ev(prompt, ["宽", "宽度"], 50.0)
            h = ev(prompt, ["高", "高度"], 60.0)
            t = ev(prompt, ["壁厚", "厚"], 10.0)
            code = (
                f"base = Box({l}, {w}, {h})\n"
                f"cut_out = Box({l - t + 2}, {w + 4}, {h - t + 2}).translate({t / 2.0 + 1}, 0, {t / 2.0 + 1})\n"
                f"part = (base - cut_out) - Cylinder(5.0, {t + 4}).translate({l / 2.0 - 15}, 0, {-h / 2.0 + t / 2.0})"
            )
            return f"已创建【L型结构安装支架】：{l}×{w}×{h} mm，壁厚 {t} mm。", code, True

        if any(k in p_low for k in ["轴套", "衬套", "阶梯轴", "bushing"]):
            od = ev(prompt, ["外径", "直径"], 40.0)
            id_in = ev(prompt, ["内径", "内孔"], 20.0)
            length = ev(prompt, ["长", "长度", "高"], 60.0)
            f_od = ev(prompt, ["法兰", "凸缘"], od + 20.0)
            code = (
                f"body = Cylinder({od / 2.0}, {length})\n"
                f"flange = Cylinder({f_od / 2.0}, 12.0).translate(0, 0, {length / 2.0 - 6.0})\n"
                f"part = (body + flange) - Cylinder({id_in / 2.0}, {length + 4})"
            )
            return f"已创建【阶梯法兰轴套】：外径 Ø{od}mm，内径 Ø{id_in}mm，长 {length}mm。", code, True

        if any(k in p_low for k in ["长方体", "方块", "底板", "基板", "box", "plate"]):
            l = nums[0] if len(nums) > 0 else 100.0
            w = nums[1] if len(nums) > 1 else 70.0
            h = nums[2] if len(nums) > 2 else 12.0
            lines = [f"part = Box({l}, {w}, {h})"]
            if "圆角" in p_low or "fillet" in p_low:
                fr = ev(prompt, ["圆角", "r"], 8.0)
                lines.append(f"part = part.fillet(part.edges().parallel_to(Z), {fr})")
            if "孔" in p_low or "hole" in p_low:
                hr = ev(prompt, ["孔", "r", "直径", "通孔"], 12.0)
                lines.append(f"part = part - Cylinder({hr}, {h + 4})")
            return f"已创建【参数化基板】：{l}×{w}×{h} mm。", "\n".join(lines), True

        dim1 = nums[0] if len(nums) > 0 else 60.0
        dim2 = nums[1] if len(nums) > 1 else 40.0
        dim3 = nums[2] if len(nums) > 2 else 20.0
        code = f"part = Box({dim1}, {dim2}, {dim3})"
        return f"已根据您的指令生成三维实体 ({dim1}×{dim2}×{dim3} mm)。", code, not has_existing_part


class EmbodiedAgentEngine:
    """Top-level Embodied Co-Pilot connected to WorkspaceSession."""

    @staticmethod
    def resolve_endpoint(base_url: str, model: str, api_key: str) -> tuple[str, str]:
        base_url = (base_url or "").strip()
        model = (model or "").strip()
        api_key = (api_key or "").strip()
        if not base_url:
            if "deepseek" in model.lower() or (api_key.startswith("sk-") and len(api_key) == 35):
                base_url = "https://api.deepseek.com/v1"
                model = model or "deepseek-chat"
            else:
                base_url = "https://api.openai.com/v1"
                model = model or "gpt-4o-mini"
        else:
            model = model or ("deepseek-chat" if "deepseek" in base_url.lower() else "gpt-4o-mini")
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url
        base_url = base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url, model
        if not base_url.endswith("/v1") and not re.search(r"/v\d+$", base_url):
            base_url += "/v1"
        return f"{base_url}/chat/completions", model

    def _build_selection_context(self, ws: WorkspaceSession, selections: list[str]) -> str:
        lines: list[str] = []
        part = ws.primary_part()
        if part is not None:
            bb = part.bbox()
            sz = [round(float(x), 2) for x in bb.size.to_tuple()]
            vol = round(float(getattr(part, "volume", 0.0)), 2)
            lines.append(f"【当前工作区主模型 `part`】：包围盒尺寸={sz} mm, 体积={vol} mm³, 拓扑面数={len(list(part.faces()))}, 拓扑边数={len(list(part.edges()))}")
            lines.append(f"【当前完整建模脚本】：\n```python\n{ws.full_script().strip()}\n```")
        if selections:
            lines.append(f"【当前用户在 3D 视口中选中的拓扑元素】：{', '.join(selections)}")
        return "\n".join(lines)

    def _call_llm(self, prompt: str, history: list[dict[str, Any]], config: dict[str, Any], context_note: str) -> str:
        endpoint, model = self.resolve_endpoint(config.get("baseUrl", ""), config.get("model", ""), config.get("apiKey", ""))
        api_doc = retrieve_api_context(prompt)
        sys_msg = SYSTEM_PROMPT + "\n\n" + context_note + ("\n\n" + api_doc if api_doc else "")

        messages = [{"role": "system", "content": sys_msg}]
        for h in (history or [])[-6:]:
            r, c = h.get("role", "user"), h.get("content", "")
            code_h = h.get("code", "")
            if r == "assistant" and code_h and "```" not in c:
                c = f"{c}\n```python\n{code_h}\n```"
            if r in ("user", "assistant"):
                messages.append({"role": r, "content": c})
        messages.append({"role": "user", "content": prompt})

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            endpoint,
            data=json.dumps({"model": model, "messages": messages, "temperature": 0.15, "max_tokens": 1400}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.get('apiKey', '').strip()}",
                "User-Agent": "SMLib-Studio-Next/2.0",
            },
        )
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    @staticmethod
    def _extract_code(text: str) -> str | None:
        matches = re.findall(r"```(?:python)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if matches:
            return matches[-1].strip()
        if "part =" in text or "part=" in text:
            return text.strip()
        return None

    def chat(
        self,
        prompt: str,
        selections: list[str] | None = None,
        history: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
        ws: WorkspaceSession | None = None,
    ) -> dict[str, Any]:
        """Execute an embodied Agent turn directly against the shared WorkspaceSession."""
        ws = ws or workspace_session
        selections = selections or []
        config = config or {}
        has_part = ws.primary_part() is not None
        use_llm = bool(config.get("apiKey") and len(str(config.get("apiKey")).strip()) > 5)

        explanation = ""
        code = ""
        replace_all = False

        if use_llm:
            try:
                ctx_note = self._build_selection_context(ws, selections)
                raw_reply = self._call_llm(prompt, history or [], config, ctx_note)
                extracted = self._extract_code(raw_reply)
                explanation = re.sub(r"```(?:python)?[\s\S]*?```", "", raw_reply).strip()
                if extracted:
                    code = extracted
                else:
                    explanation, code, replace_all = LocalEmbodiedResolver.resolve(prompt, selections, has_part)
            except Exception as llm_err:
                exp_loc, code, replace_all = LocalEmbodiedResolver.resolve(prompt, selections, has_part)
                explanation = f"*(外部大模型未就绪: {llm_err}，已由内置具身 CAD 引擎直接执行)*\n{exp_loc}"
        else:
            explanation, code, replace_all = LocalEmbodiedResolver.resolve(prompt, selections, has_part)

        try:
            state = ws.execute_step(
                code=code,
                label=f"Agent: {prompt[:24]}",
                operator_id="agent",
                selections=selections,
                replace_all=replace_all,
            )
            return {
                "ok": True,
                "reply": explanation,
                "code": ws.full_script(),
                "step_code": code,
                "state": state,
                "error": None,
            }
        except Exception as exec_err:
            return {
                "ok": False,
                "reply": explanation or "执行建模脚本时遇到几何约束冲突。",
                "code": code,
                "state": ws.get_state(),
                "error": str(exec_err),
            }

    def test_connection(self, config: dict[str, Any]) -> dict[str, Any]:
        api_key = str(config.get("apiKey", "")).strip()
        if not api_key:
            return {"ok": False, "error": "请先填写 API Key"}
        endpoint, model = self.resolve_endpoint(config.get("baseUrl", ""), config.get("model", ""), api_key)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            endpoint,
            data=json.dumps({"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}", "User-Agent": "SMLib-Studio-Next/2.0"},
        )
        try:
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                json.loads(resp.read().decode("utf-8"))
                return {"ok": True, "endpoint": endpoint, "model": model, "latency_ms": round((time.perf_counter() - t0) * 1000)}
        except Exception as exc:
            return {"ok": False, "endpoint": endpoint, "model": model, "error": str(exc)}


embodied_agent = EmbodiedAgentEngine()
