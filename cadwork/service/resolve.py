"""Turning what a person says into an address in the document.

A non-expert says "把左边的沉头改大点" and should not have to know the
document id of that feature. Two things make that possible, both deterministic:

* `summarize` names every feature the way a person would ("沉头孔 Ø18"),
  and reports what the build produced, so a model can talk about the document
  without reading raw JSON.
* `resolve` turns a phrase into ranked candidates with reasons and, when it is
  not sure, the clarifying question to ask instead of guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from cadwork.design.document import Document, Feature

# What people call a kind of feature.
NOUNS: dict[str, tuple[str, ...]] = {
    "孔": ("hole", "k_hole"),
    "洞": ("hole", "k_hole"),
    "孔洞": ("hole", "k_hole"),
    "螺孔": ("hole", "k_hole"),
    "板": ("solid_box", "k_box"),
    "方块": ("solid_box", "k_box"),
    "长方体": ("solid_box", "k_box"),
    "圆柱": ("solid_cylinder", "k_cylinder"),
    "圆盘": ("solid_cylinder", "k_cylinder"),
    "抽壳": ("shell", "k_shell"),
    "壁": ("shell", "k_shell"),
    "倒角": ("chamfer", "k_chamfer"),
    "圆角": ("fillet", "k_fillet", "blend_group"),
    "拉伸": ("extrude", "k_extrude"),
    "旋转": ("revolve_profile", "hub_revolve", "k_revolve", "k_rotate"),
    "扫掠": ("sweep", "k_sweep"),
    "阵列": ("pattern",),
}

# Words that pick one variant of a feature.
KIND_WORDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "沉头": ("kind", ("counterbore",)),
    "沉孔": ("kind", ("counterbore", "countersink")),
    "沉锥": ("kind", ("countersink",)),
    "锥形": ("kind", ("countersink",)),
    "通孔": ("kind", ("simple",)),
    "普通孔": ("kind", ("simple",)),
}

POSITIONS = {
    "左": ("x", -1),
    "右": ("x", 1),
    "上": ("z", 1),
    "下": ("z", -1),
    "前": ("y", -1),
    "后": ("y", 1),
}

NUMBER = re.compile(r"\d+(?:\.\d+)?")


def describe(feature: Feature) -> str:
    """How a person would refer to this feature."""
    params = feature.params
    kind = feature.type
    if kind == "hole":
        shape = {"counterbore": "沉头孔", "countersink": "沉孔", "simple": "通孔",
                 }.get(str(params.get("kind")), "孔")
        diameter = params.get("diameter")
        extra = ""
        if str(params.get("kind")) == "counterbore" and params.get("cb_diameter"):
            extra = f"（Ø{_num(params['cb_diameter'])} 沉头）"
        elif str(params.get("kind")) == "countersink" and params.get("cs_diameter"):
            extra = f"（Ø{_num(params['cs_diameter'])} 锥口）"
        return f"{shape} Ø{_num(diameter)}{extra}"
    if kind == "solid_box":
        return (f"板 {_num(params.get('length'))}×{_num(params.get('width'))}"
                f"×{_num(params.get('height'))}")
    if kind == "solid_cylinder":
        return f"圆柱 Ø{_num(params.get('radius', 0) * 2)}×{_num(params.get('height'))}"
    if kind == "chamfer":
        return f"倒角 {_num(params.get('length'))}"
    if kind == "fillet":
        return f"圆角 {_num(params.get('radius'))}"
    if kind == "shell":
        return f"抽壳 壁厚 {_num(params.get('thickness'))}"
    if kind == "extrude":
        return f"拉伸 {_num(params.get('amount'))}"
    if kind == "k_cylinder":
        return f"圆柱 Ø{_num((params.get('radius') or 0) * 2)}×{_num(params.get('height'))}"
    if kind == "k_box":
        return (f"方块 {_num(params.get('length'))}×{_num(params.get('width'))}"
                f"×{_num(params.get('height'))}")
    if kind == "k_chamfer":
        return f"倒角 {_num(params.get('length'))}"
    if kind == "k_fillet":
        return f"圆角 {_num(params.get('radius'))}"
    if kind == "blend_group":
        radius = params.get("radius")
        return f"圆角组 {_num(radius)}" if radius is not None else "圆角组"
    if kind == "pattern":
        count = params.get("count")
        return f"阵列 {_num(count)} 个" if count is not None else "阵列"
    if kind == "k_cut":
        return "切除"
    if kind == "k_fuse":
        return "合并"
    if kind == "k_translate":
        return "平移"
    if kind == "k_move_faces":
        return "面调整"
    if kind in ("k_revolve", "k_rotate"):
        return "旋转"
    if kind == "k_extrude":
        return "拉伸"
    if kind == "k_shell":
        return f"抽壳 壁厚 {_num(params.get('thickness'))}"
    return kind


def _num(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:g}"


def _mentions_id(text: str, feature_id: str) -> bool:
    token = re.escape(feature_id.lower())
    return re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", text) is not None


@dataclass
class Match:
    feature_id: str
    type: str
    what: str
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {"id": self.feature_id, "type": self.type, "what": self.what,
                "score": round(self.score, 2), "reasons": self.reasons}


def summarize(document: Document, result: Any = None) -> dict[str, Any]:
    """A compact, talk-able view of the document: names, numbers, state."""
    features = []
    for feature in document.features:
        features.append({
            "id": feature.id,
            "type": feature.type,
            "what": describe(feature),
            "enabled": feature.enabled,
            "params": {key: value for key, value in feature.params.items()
                       if isinstance(value, (int, float, str, bool))},
            "note": feature.note or "",
            "actor": feature.actor,
        })
    payload: dict[str, Any] = {
        "document": {"id": document.id, "name": document.name,
                     "version": document.version, "features": len(features)},
        "features": features,
        "vocabulary": sorted({entry["what"].split(" ")[0] for entry in features}),
    }
    if result is not None and getattr(result, "final", None) is not None:
        final = result.final
        payload["output"] = {
            "faces": len(final.faces()),
            "volume": round(float(final.volume), 1),
            "checks_failed": sum(1 for item in result.features
                                 for check in item.checks if not check.ok),
        }
    return payload


def resolve(document: Document, phrase: str) -> dict[str, Any]:
    """Rank features against a phrase a person would say."""
    text = phrase.strip()
    lowered = text.lower()
    numbers = [float(item) for item in NUMBER.findall(text)]

    words: list[tuple[str, tuple[str, ...]]] = []
    for noun, types in NOUNS.items():
        if noun in text:
            words.append((noun, types))
    kinds = [(word, spec) for word, spec in KIND_WORDS.items() if word in text]
    positions = [(word, POSITIONS[word]) for word in POSITIONS if word in text]
    wants_last = any(word in text for word in ("最后", "刚才", "新加", "最新"))

    matches: list[Match] = []
    for index, feature in enumerate(document.features):
        score = 0.0
        reasons: list[str] = []
        if _mentions_id(lowered, feature.id):
            score += 10
            reasons.append(f"直接点名 {feature.id}")
        for noun, types in words:
            if feature.type in types:
                score += 3
                reasons.append(f"类型是「{noun}」")
        for word, (param_name, wanted) in kinds:
            if str(feature.params.get(param_name)) in wanted:
                score += 4
                reasons.append(f"参数符合「{word}」")
        for value in numbers:
            for key, raw in feature.params.items():
                if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                    continue
                if abs(float(raw) - value) <= max(0.01, abs(value) * 0.001):
                    score += 2
                    reasons.append(f"{key} = {_num(raw)} 与「{_num(value)}」一致")
                    break
        for word, (axis, sign) in positions:
            raw = feature.params.get(axis)
            if isinstance(raw, (int, float)) and sign * float(raw) > 0:
                score += 2
                reasons.append(f"在「{word}」侧（{axis}={_num(raw)}）")
        if wants_last and index == len(document.features) - 1:
            score += 2
            reasons.append("是最后一个特征")
        if score > 0:
            matches.append(Match(feature.id, feature.type, describe(feature),
                                 score, reasons))

    matches.sort(key=lambda item: (-item.score, item.feature_id))
    confident = False
    question = None
    if matches:
        top = matches[0].score
        second = matches[1].score if len(matches) > 1 else 0.0
        confident = top >= 2 and (len(matches) == 1 or (top - second) >= 2)
        if not confident:
            names = "、".join(f"{item.feature_id}（{item.what}）" for item in matches[:3])
            question = f"你指的是哪一个：{names}？"
    else:
        question = ("我在这个文档里没找到对应的特征；可以说说它是什么形状，"
                    "或者它是左边还是右边那一个。")
    return {
        "phrase": phrase,
        "confident": confident,
        "matches": [item.to_json() for item in matches],
        "question": question,
    }


def resolve_gate(
    document: Document,
    phrase: str,
    anchor: str | None = None,
) -> dict[str, Any]:
    """Decide whether a spoken reference is safe to write against.

    A picked feature is already an address; otherwise only a confident match
    yields a writable feature id. Everything else must go back to the person as
    a concrete choice, never as a guessed edit.
    """
    payload = resolve(document, phrase)
    if anchor:
        payload.update(can_write=True, resolved_id=anchor, anchor=anchor)
        return payload
    matches = payload["matches"]
    if payload["confident"] and matches:
        payload.update(can_write=True, resolved_id=matches[0]["id"], anchor=None)
        return payload
    if matches:
        options = "；".join(
            f"{item['id']}（{item['what']}"
            + (f"；{item['reasons'][0]}" if item.get("reasons") else "")
            + "）"
            for item in matches[:4]
        )
        question = f"你指的是哪一个：{options}？"
    else:
        question = payload["question"] or "没有找到对应的特征，请换一种说法。"
    payload.update(can_write=False, resolved_id=None, anchor=None, question=question)
    return payload


def names_present(document: Document) -> Iterable[str]:
    for feature in document.features:
        yield feature.id
