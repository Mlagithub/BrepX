"""Turning what a person says into an address in the document.

A non-expert says "把左边的沉头改大点" and should not have to know that the
feature is called `h2`. Two things make that possible, both deterministic:

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
    "孔": ("hole",),
    "洞": ("hole",),
    "孔洞": ("hole",),
    "螺孔": ("hole",),
    "板": ("solid_box",),
    "方块": ("solid_box",),
    "长方体": ("solid_box",),
    "圆柱": ("solid_cylinder",),
    "圆盘": ("solid_cylinder",),
    "抽壳": ("shell",),
    "壁": ("shell",),
    "倒角": ("chamfer",),
    "圆角": ("fillet",),
    "拉伸": ("extrude",),
    "旋转": ("revolve_profile", "hub_revolve"),
    "扫掠": ("sweep",),
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
IDENT = re.compile(r"\b[a-z]\d+\b", re.IGNORECASE)


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
    return kind


def _num(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:g}"


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
    idents = [item.lower() for item in IDENT.findall(lowered)]

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
        if feature.id.lower() in idents:
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


def names_present(document: Document) -> Iterable[str]:
    for feature in document.features:
        yield feature.id
