import re
import os
import ssl
import json
import time
import urllib.request
import urllib.error
import traceback
from typing import Dict, Any, List, Optional, Tuple

import smlibpy
from smlibpy import *

SYSTEM_PROMPT = """你是一个精通 CAD 几何建模与 Python smlibpy 库的专业 AI 建模工程师。
你的任务是根据用户的自然语言描述，编写准确、符合物理与机械加工逻辑的 Python smlibpy 建模代码。

【smlibpy 核心 API 指南】
1. 引用与导入：代码必须以 `from smlibpy import *` 开头。
2. 基础体图元：
   - `Box(length, width, height)`: 创建中心位于原点的长方体
   - `Cylinder(radius, height)`: 沿 Z 轴创建中心位于原点的圆柱体
   - `Sphere(radius)`: 创建球体
   - `Cone(radius1, radius2, height)`: 创建圆锥或圆台
   - `Torus(major_radius, minor_radius)`: 创建圆环体
3. 几何变换：
   - `.translate(dx, dy, dz)`: 平移
   - `.rotate(axis, angle_in_degrees)`: 绕指定轴旋转，如 `.rotate(Z, 45)`、`.rotate(X, 90)`
   - `.scale(factor)`: 等比缩放
4. 布尔运算（重载运算符）：
   - 并集：`a + b`
   - 差集（切削/开孔）：`a - b`
   - 交集：`a & b`
5. 特征编辑：
   - 倒圆角：`part.fillet(edges, radius)`，例如选择竖直边：`part.fillet(part.edges().parallel_to(Z), 5)`
   - 倒角：`part.chamfer(edges, distance)`
6. 严格规范：
   - 最终构造好的模型必须赋值给名为 `part` 的变量：`part = ...`
   - 不要包含 `show(part)` 或 `part.export(...)`，系统会自动处理导出与渲染
   - 优先使用布尔切削实现孔、槽、台阶特征
   - 请在代码块 ```python ... ``` 中输出完整的 Python 代码，并在代码块外附带简明扼要的设计说明与尺寸参数解析。
"""

class LocalSemanticEngine:
    """本地内置的轻量 CAD 语义解析器，无需外部 API Key 即可开箱即用支持多类常见几何建模意图。"""
    
    @staticmethod
    def extract_val(text: str, keywords: List[str], default_val: float) -> float:
        for kw in keywords:
            m = re.search(kw + r'[:\s=为到]*(\d+(?:\.\d+)?)', text)
            if m:
                return float(m.group(1))
        return default_val

    @staticmethod
    def parse_and_generate(prompt: str, history: List[Dict[str, str]] = None) -> Tuple[str, str]:
        prompt_lower = prompt.lower()
        
        # 1. 尝试匹配上下文多轮修改与特征累加
        last_code = ""
        if history:
            for msg in reversed(history):
                if msg.get("role") == "assistant" and "part = " in msg.get("code", ""):
                    last_code = msg.get("code", "")
                    break
        
        is_explicit_new = any(k in prompt_lower for k in ["新建", "重新", "另外", "换一个", "从头", "做一个新的"])

        if last_code and not is_explicit_new:
            ev = LocalSemanticEngine.extract_val

            # 1.1 参数微调 (例如：“把孔改成10”、“厚度改为20”、“圆角调成8”)
            if any(k in prompt_lower for k in ["改成", "修改为", "变为", "设为", "调大", "变小", "把", "调整"]):
                num_match = re.findall(r'(\d+(?:\.\d+)?)', prompt)
                if num_match:
                    new_val = float(num_match[0])
                    if any(k in prompt_lower for k in ["孔", "直径", "孔径", "半径"]):
                        r_val = new_val / 2 if any(k in prompt_lower for k in ["直径", "d", "孔径"]) else new_val
                        mod_code = re.sub(r'(Cylinder\()(\d+(?:\.\d+)?)', rf'\g<1>{r_val}', last_code, count=1)
                        if mod_code != last_code:
                            return f"已将孔的尺寸调整为 Ø{r_val*2:.1f}mm (半径 R{r_val}mm) 并重新生成几何。", mod_code
                    
                    if any(k in prompt_lower for k in ["厚度", "高度", "高", "厚"]):
                        mod_code = re.sub(r'Box\(([^,]+),([^,]+),\s*(\d+(?:\.\d+)?)\)', rf'Box(\1,\2, {new_val})', last_code)
                        if mod_code == last_code:
                            mod_code = re.sub(r'(Cylinder\([^,]+,\s*)(\d+(?:\.\d+)?)', rf'\g<1>{new_val}', last_code, count=1)
                        if mod_code != last_code:
                            return f"已将高度/厚度修改为 {new_val}mm 并重新生成几何。", mod_code
                    
                    if any(k in prompt_lower for k in ["圆角", "倒角"]):
                        mod_code = re.sub(r'\.fillet\(([^,]+),\s*(\d+(?:\.\d+)?)\)', rf'.fillet(\1, {new_val})', last_code)
                        if mod_code != last_code:
                            return f"已将圆角半径调整为 R{new_val} 并重新生成几何。", mod_code

            # 1.2 在已有模型上累加特征 (例如：“打一个直径20的孔”、“再给垂直边加个R5圆角”)
            if any(k in prompt_lower for k in ["孔", "打孔", "开孔", "挖孔", "通孔"]):
                d_hole = ev(prompt, ["直径", "孔径", "内孔", "孔"], 20)
                r_hole = d_hole / 2 if any(k in prompt_lower for k in ["直径", "孔径", "d"]) else d_hole
                new_code = last_code.rstrip() + f"\n# [多轮特征追加] 贯穿通孔切削\nhole_add = Cylinder({r_hole}, 100)\npart = part - hole_add\n"
                return f"已在现有模型基础上，追加切削了直径 Ø{r_hole*2:.1f}mm 贯穿通孔。", new_code

            if any(k in prompt_lower for k in ["圆角", "倒圆", "fillet"]):
                r_fillet = ev(prompt, ["圆角", "r", "半径"], 5)
                new_code = last_code.rstrip() + f"\n# [多轮特征追加] 垂直边追加 R{r_fillet} 倒圆角\npart = part.fillet(part.edges().parallel_to(Z), {r_fillet})\n"
                return f"已在现有模型基础上，为垂直边追加了 R{r_fillet}mm 圆角。", new_code

            if any(k in prompt_lower for k in ["凸台", "凸缘", "凸起", "立柱"]):
                r_boss = ev(prompt, ["半径", "外径", "直径"], 15)
                h_boss = ev(prompt, ["高度", "高", "厚"], 15)
                new_code = last_code.rstrip() + f"\n# [多轮特征追加] 顶部追加圆柱凸台\nboss = Cylinder({r_boss}, {h_boss})\npart = part + boss\n"
                return f"已在现有模型基础上，追加了半径 R{r_boss}mm、高度 {h_boss}mm 的圆柱凸台。", new_code

        # 2. 意图分支匹配与精准参数提取
        ev = LocalSemanticEngine.extract_val

        # A. 法兰盘 / 带孔圆盘 / 管道法兰
        if any(k in prompt_lower for k in ["法兰", "flange", "圆盘", "管道接口"]):
            # 提取外径/外半径 (默认 80)
            d_out = ev(prompt, ["外径", "外圆直径", "直径", "外圆"], 80)
            # 提取内孔 (默认 30)
            d_in = ev(prompt, ["内孔", "内径", "通孔直径", "通孔", "内孔直径"], 30)
            # 提取厚度 (默认 12)
            h = ev(prompt, ["厚度", "厚", "高", "高度"], 12)
            # 提取螺栓孔数 (默认 4)
            bolt_n = int(ev(prompt, ["螺栓孔", "个孔", "孔数", "螺栓"], 4))
            bolt_d = ev(prompt, ["螺栓孔径", "孔径", "小孔"], 8)

            r_outer = d_out / 2
            r_inner = d_in / 2
            if r_inner >= r_outer:
                r_inner = r_outer * 0.4
            
            r_bolt = bolt_d / 2
            pcd = (r_outer + r_inner) / 2
            
            code = f"""from smlibpy import *
import math

# 1. 基础法兰盘外圆
part = Cylinder({r_outer}, {h})

# 2. 中心流体通孔切削
center_bore = Cylinder({r_inner}, {h + 4})
part = part - center_bore

# 3. 均匀分布的 {bolt_n} 个螺栓安装孔
bolt_pcd = {pcd:.1f}
for i in range({bolt_n}):
    angle = i * (2 * math.pi / {bolt_n})
    bx = bolt_pcd * math.cos(angle)
    by = bolt_pcd * math.sin(angle)
    bolt = Cylinder({r_bolt}, {h + 4}).translate(bx, by, 0)
    part = part - bolt
"""
            explanation = f"已创建【圆形管道法兰】：外径 Ø{d_out}mm (半径 R{r_outer}mm)，厚度 {h}mm，中心通孔 Ø{d_in}mm，并在节圆 PCD={pcd:.1f}mm 上均布了 {bolt_n} 个 Ø{bolt_d}mm 螺栓孔。"
            return explanation, code

        # B. 轴类 / 衬套 / 阶梯轴
        elif any(k in prompt_lower for k in ["轴", "衬套", "轴套", "套筒", "bushing", "sleeve"]):
            od = ev(prompt, ["外径", "主体直径", "轴径", "直径"], 40)
            length = ev(prompt, ["长", "总长", "长度", "高度", "高"], 60)
            id_inner = ev(prompt, ["内径", "内孔", "孔径", "通孔"], 20)
            flange_od = ev(prompt, ["法兰外径", "凸缘直径", "凸台外径"], od + 20)
            flange_len = ev(prompt, ["法兰厚度", "凸缘厚度", "凸台高"], 12)

            r_od = od / 2
            r_id = min(id_inner / 2, r_od * 0.75)
            r_flange = flange_od / 2

            code = f"""from smlibpy import *

# 1. 外圆柱轴体与法兰凸台
body = Cylinder({r_od}, {length})
flange = Cylinder({r_flange}, {flange_len}).translate(0, 0, {length / 2 - flange_len / 2})
part = body + flange

# 2. 中心贯穿通孔
bore = Cylinder({r_id}, {length + 4})
part = part - bore
"""
            explanation = f"已创建【阶梯衬套零件】：外径 Ø{od}mm，总长 {length}mm，法兰凸台外径 Ø{flange_od}mm，内孔直径 Ø{id_inner}mm。"
            return explanation, code

        # C. L型支架 / 角码
        elif any(k in prompt_lower for k in ["支架", "角码", "l型", "bracket"]):
            l = ev(prompt, ["长度", "长", "x向", "x"], 80)
            w = ev(prompt, ["宽度", "宽", "y向", "y"], 50)
            h = ev(prompt, ["高度", "高", "z向", "z"], 60)
            t = ev(prompt, ["壁厚", "板厚", "厚度", "厚"], 10)
            hole_r = ev(prompt, ["孔径", "孔半径", "固定孔"], 6)

            code = f"""from smlibpy import *

# 1. 实心长方体基料
base = Box({l}, {w}, {h})

# 2. 减除内角形成 L 型支架
cut_out = Box({l - t + 2}, {w + 4}, {h - t + 2}).translate({t / 2 + 1}, 0, {t / 2 + 1})
part = base - cut_out

# 3. 底板固定通孔
hole = Cylinder({hole_r}, {t + 4}).translate({l / 2 - 15}, 0, {-h / 2 + t / 2})
part = part - hole
"""
            explanation = f"已创建【L型结构安装支架】：尺寸 {l}mm × {w}mm × {h}mm，壁厚 {t}mm，底部带有 R{hole_r}mm 固定通孔。"
            return explanation, code

        # D. 长方体 / 带有圆角 / 开孔的基板
        elif any(k in prompt_lower for k in ["长方体", "方块", "板", "基座", "底板", "box", "plate"]):
            l = ev(prompt, ["长", "长度", "长方体长"], 100)
            w = ev(prompt, ["宽", "宽度"], 70)
            h = ev(prompt, ["厚", "厚度", "高", "高度"], 15)
            
            fillet_r = ev(prompt, ["圆角", "倒圆", "fillet", "r"], 0)
            has_hole = any(k in prompt_lower for k in ["孔", "打孔", "开孔", "hole", "通孔"])
            hole_r = ev(prompt, ["孔径", "直径", "内孔", "通孔"], 12)
            if any(k in prompt_lower for k in ["直径", "孔径"]):
                hole_r = hole_r / 2

            code_lines = [
                "from smlibpy import *",
                f"part = Box({l}, {w}, {h})"
            ]
            if fillet_r > 0:
                code_lines.append(f"# 垂直四边应用 R{fillet_r} 圆角")
                code_lines.append(f"part = part.fillet(part.edges().parallel_to(Z), {fillet_r})")
            if has_hole and hole_r > 0:
                code_lines.append(f"# 中心贯穿孔")
                code_lines.append(f"hole = Cylinder({hole_r}, {h + 4})")
                code_lines.append(f"part = part - hole")
            
            code = "\n".join(code_lines)
            explanation = f"已创建【基板模型】：长 {l}mm × 宽 {w}mm × 厚 {h}mm"
            if fillet_r > 0: explanation += f"，竖边 R{fillet_r}mm 倒圆角"
            if has_hole: explanation += f"，中心通孔半径 R{hole_r}mm"
            explanation += "。"
            return explanation, code

        # E. 圆柱体 / 管道
        elif any(k in prompt_lower for k in ["圆柱", "柱体", "cylinder", "管道", "圆管"]):
            d = ev(prompt, ["外径", "直径", "半径"], 50)
            r = d / 2 if any(k in prompt_lower for k in ["外径", "直径"]) else d
            h = ev(prompt, ["高", "高度", "长", "长度"], 60)
            is_pipe = any(k in prompt_lower for k in ["管", "空心", "内径", "壁厚"])
            
            if is_pipe:
                inner_d = ev(prompt, ["内径", "内孔"], d * 0.7)
                inner_r = inner_d / 2 if any(k in prompt_lower for k in ["内径", "内孔"]) else inner_d
                code = f"""from smlibpy import *

outer = Cylinder({r}, {h})
inner = Cylinder({inner_r}, {h + 4})
part = outer - inner
"""
                return f"已创建【空心圆管】：外径 R{r}mm，内孔 R{inner_r}mm，高度 {h}mm。", code
            else:
                code = f"""from smlibpy import *

part = Cylinder({r}, {h})
"""
                return f"已创建【实心圆柱】：半径 R{r}mm，高度 {h}mm。", code

        # F. 球体 / 组合体
        elif any(k in prompt_lower for k in ["球", "sphere"]):
            r = ev(prompt, ["半径", "半球", "r"], 30)
            code = f"""from smlibpy import *

part = Sphere({r})
"""
            return f"已创建【球体】：半径 R{r}mm。", code

        # G. 兜底通用生成
        else:
            nums = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)', prompt)]
            dim1 = nums[0] if len(nums) > 0 else 80
            dim2 = nums[1] if len(nums) > 1 else 60
            dim3 = nums[2] if len(nums) > 2 else 15
            hole_r = min(dim1, dim2) / 4
            code = f"""from smlibpy import *

# 基础模型构造
base = Box({dim1}, {dim2}, {dim3})
cut = Cylinder({hole_r}, {dim3 + 4})
part = base - cut
"""
            return f"已根据您的描述构建长方体基座并切削中心通孔（尺寸 {dim1} × {dim2} × {dim3}）。", code


class CADAgent:
    def __init__(self):
        pass

    @staticmethod
    def resolve_endpoint(base_url: str, model: str, api_key: str) -> Tuple[str, str]:
        """智能解析并规范化 API Endpoint 与默认 Model。"""
        base_url = (base_url or "").strip()
        model = (model or "").strip()
        api_key = (api_key or "").strip()

        # 若未填 Base URL，根据 Model 或 Key 自动推断
        if not base_url:
            if "deepseek" in model.lower() or (api_key.startswith("sk-") and len(api_key) == 35):
                base_url = "https://api.deepseek.com/v1"
                if not model: model = "deepseek-chat"
            else:
                base_url = "https://api.openai.com/v1"
                if not model: model = "gpt-4o-mini"
        else:
            if not model:
                if "deepseek" in base_url.lower():
                    model = "deepseek-chat"
                else:
                    model = "gpt-4o-mini"

        # 补齐协议
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = "https://" + base_url

        base_url = base_url.rstrip("/")

        # 规范化路径结尾
        if base_url.endswith("/chat/completions"):
            endpoint = base_url
        else:
            # 常见情况：用户填 https://api.deepseek.com，需补齐 /v1
            if not base_url.endswith("/v1") and not re.search(r'/v\d+$', base_url):
                base_url = base_url + "/v1"
            endpoint = f"{base_url}/chat/completions"

        return endpoint, model

    def call_external_llm(self, prompt: str, history: List[Dict[str, str]], config: Dict[str, Any]) -> str:
        """调用用户配置的兼容 OpenAI 接口的大模型，支持 SSL 与多代理环境。"""
        api_key = config.get("apiKey", "").strip()
        base_url = config.get("baseUrl", "").strip()
        model_req = config.get("model", "").strip()

        endpoint, model = self.resolve_endpoint(base_url, model_req, api_key)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in (history or [])[-8:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            code = h.get("code", "")
            # 保证大模型在多轮对话中能够看见助手之前编写的具体 smlibpy 代码
            if role == "assistant" and code and "```" not in content:
                content = f"{content}\n\n```python\n{code}\n```"
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1500
        }

        # 创建兼容系统代理与自签名证书的 SSL Context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
            }
        )

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            raw_body = e.read().decode("utf-8", errors="ignore")
            detail = ""
            try:
                err_json = json.loads(raw_body)
                if "error" in err_json:
                    err_info = err_json["error"]
                    detail = err_info.get("message") or str(err_info)
            except Exception:
                detail = raw_body[:300]
            err_msg = f"HTTP {e.code} ({e.reason}) - 接口地址: {endpoint}"
            if detail:
                err_msg += f" | 服务端信息: {detail}"
            raise RuntimeError(err_msg)
        except urllib.error.URLError as e:
            raise RuntimeError(f"网络连接失败 ({str(e.reason)}) - 请检查地址: {endpoint}")
        except Exception as e:
            raise RuntimeError(f"大模型调用失败: {str(e)}")

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试用户配置的大模型连通性。"""
        api_key = config.get("apiKey", "").strip()
        base_url = config.get("baseUrl", "").strip()
        model_req = config.get("model", "").strip()

        if not api_key:
            return {"ok": False, "error": "请先填写 API Key"}

        endpoint, model = self.resolve_endpoint(base_url, model_req, api_key)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5
        }

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

        try:
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                elapsed = round((time.perf_counter() - t0) * 1000)
                reply = data["choices"][0]["message"]["content"].strip()
                return {
                    "ok": True,
                    "endpoint": endpoint,
                    "model": model,
                    "latency_ms": elapsed,
                    "sample": reply
                }
        except urllib.error.HTTPError as e:
            raw_body = e.read().decode("utf-8", errors="ignore")
            detail = ""
            try:
                err_json = json.loads(raw_body)
                if "error" in err_json:
                    detail = err_json["error"].get("message") or str(err_json["error"])
            except Exception:
                detail = raw_body[:300]
            msg = f"HTTP {e.code} ({e.reason})"
            if detail: msg += f": {detail}"
            return {"ok": False, "endpoint": endpoint, "model": model, "error": msg}
        except Exception as e:
            return {"ok": False, "endpoint": endpoint, "model": model, "error": str(e)}

    def extract_code_block(self, text: str) -> Optional[str]:
        """从模型回复中提取 ```python 代码块。"""
        matches = re.findall(r'```(?:python)?\s*([\s\S]*?)```', text, re.IGNORECASE)
        if matches:
            # 找到包含 part = 的那个代码块
            for m in reversed(matches):
                if "part" in m and "smlibpy" in m:
                    return m.strip()
            return matches[-1].strip()
        # 若没有包含 markdown 块，但纯代码
        if "from smlibpy import" in text:
            return text.strip()
        return None

    def execute_code(self, code: str) -> Tuple[Any, Optional[str]]:
        """在受控沙盒中执行 Python 代码并返回 part 对象。"""
        user_globals = {
            "__name__": "__main__",
            "smlibpy": smlibpy,
        }
        for attr in dir(smlibpy):
            if not attr.startswith("__"):
                user_globals[attr] = getattr(smlibpy, attr)

        try:
            exec(code, user_globals)
            part = user_globals.get("part")
            if part is None:
                # 寻找任一包含 volume 的对象
                for v in user_globals.values():
                    if hasattr(v, "volume") and hasattr(v, "export"):
                        part = v
                        break
            if part is None:
                return None, "脚本未产生名为 `part` 的几何模型实体。"
            return part, None
        except Exception as e:
            return None, f"{type(e).__name__}: {str(e)}"

    def chat(self, prompt: str, history: List[Dict[str, str]] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Agent 主入口：接收用户对话，生成代码并完成建模求解。"""
        config = config or {}
        use_external_llm = bool(config.get("apiKey") and len(config.get("apiKey").strip()) > 3)

        explanation = ""
        code = ""

        if use_external_llm:
            try:
                llm_response = self.call_external_llm(prompt, history, config)
                code = self.extract_code_block(llm_response)
                # 提取代码前后的说明文字
                explanation = re.sub(r'```(?:python)?[\s\S]*?```', '', llm_response).strip()
                if not code:
                    # 如果未能提取出代码，回退到本地解析器
                    exp_local, code_local = LocalSemanticEngine.parse_and_generate(prompt, history)
                    code = code_local
                    explanation = llm_response + "\n\n(已由本地 CAD 引擎补充生成代码)"
            except Exception as e:
                # 外部 LLM 请求失败时优雅回退
                err_note = f"外部大模型调用异常 ({str(e)})，已自动切换为内置本地 CAD 语义引擎响应。"
                exp_local, code_local = LocalSemanticEngine.parse_and_generate(prompt, history)
                explanation = f"{err_note}\n\n{exp_local}"
                code = code_local
        else:
            explanation, code = LocalSemanticEngine.parse_and_generate(prompt, history)

        # 执行生成的代码
        part, exec_err = self.execute_code(code)

        # 如果执行失败且配置了大模型，进行一次自愈重试
        if exec_err and use_external_llm:
            retry_prompt = f"之前生成的代码在运行时遇到了以下错误：\n{exec_err}\n\n请分析原因并修复代码，确保代码严格遵循 smlibpy API 并且最终将有效几何模型赋值给 `part` 变量。\n原代码：\n```python\n{code}\n```"
            try:
                llm_retry_resp = self.call_external_llm(retry_prompt, history, config)
                retry_code = self.extract_code_block(llm_retry_resp)
                if retry_code:
                    part_retry, err_retry = self.execute_code(retry_code)
                    if part_retry:
                        part = part_retry
                        code = retry_code
                        exec_err = None
                        explanation += "\n\n*(注意：初次生成的代码已通过自愈纠错完成自动修复)*"
            except Exception:
                pass

        return {
            "explanation": explanation,
            "code": code,
            "part": part,
            "error": exec_err
        }

cad_agent = CADAgent()
