"""Resolve semantic references against built feature outputs."""

from __future__ import annotations

from typing import Any, Mapping

from .document import Filter, Ref

_SELECTS = {"self", "faces", "edges", "solids", "vertices"}

_METHODS = {
    "top", "bottom", "left", "right", "front", "back",
    "nearest", "at", "within",
    "concave", "convex", "cylinders", "planar", "circles", "lines", "fillets",
    "parallel_to", "perpendicular_to", "facing",
    "largest", "smallest", "one", "of_type", "smooth",
}
_PROPERTIES = {"first", "last", "count"}
_AXIS_METHODS = {"parallel_to", "perpendicular_to", "facing"}


class RefError(Exception):
    def __init__(self, code: str, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint


def resolve(ref: Ref, outputs: Mapping[str, Any]) -> Any:
    if ref.source not in outputs:
        raise RefError(
            "REF_NOT_FOUND",
            f"source {ref.source!r} has no output yet",
            hint="references must point to an earlier, enabled feature",
        )
    target = outputs[ref.source]
    if ref.select == "self":
        return target
    if ref.select not in _SELECTS:
        raise RefError("REF_UNSUPPORTED", f"unsupported select {ref.select!r}")

    accessor = getattr(target, ref.select, None)
    if not callable(accessor):
        raise RefError("REF_UNSUPPORTED", f"output has no {ref.select}()")
    items = accessor()

    for item in ref.filters:
        items = _apply(items, item)
    return items


def _apply(items: Any, item: Filter) -> Any:
    name = item.method
    if name in _PROPERTIES:
        if item.args or item.kwargs:
            raise RefError("REF_INVALID_ARG", f"{name} takes no arguments")
        try:
            return getattr(items, name)
        except IndexError as exc:
            raise RefError("REF_EMPTY", f"{name}: empty selection") from exc
        except AttributeError as exc:
            raise RefError(
                "REF_UNSUPPORTED",
                f"{name} is not available after {type(items).__name__}",
            ) from exc

    if name not in _METHODS:
        raise RefError("REF_UNSUPPORTED", f"filter method {name!r} is not allowed")
    method = getattr(items, name, None)
    if not callable(method):
        raise RefError("REF_UNSUPPORTED", f"{name} is not available on this value")

    args = [_argument(name, value) for value in item.args]
    kwargs = {key: _argument(name, value) for key, value in item.kwargs}
    try:
        return method(*args, **kwargs)
    except TypeError as exc:
        raise RefError("REF_INVALID_ARG", f"{name}: {exc}") from exc
    except IndexError as exc:
        raise RefError("REF_EMPTY", f"{name}: empty selection") from exc
    except Exception as exc:  # kernel rejection is a normal outcome
        raise RefError("REF_UNSUPPORTED", f"{name}: {exc}") from exc


def _argument(name: str, value: Any) -> Any:
    if name in _AXIS_METHODS and isinstance(value, str):
        from cadwork.smlib import AxisName

        return AxisName.get(value)
    return value


def count(value: Any) -> int:
    return len(value) if hasattr(value, "__len__") else 1


def single(value: Any) -> Any:
    """Return the sole element, or raise a precise cardinality error."""
    total = count(value)
    if total == 1:
        return value if not hasattr(value, "__len__") else value.first
    code = "REF_EMPTY" if total == 0 else "REF_AMBIGUOUS"
    raise RefError(code, f"expected exactly 1 element, got {total}")
