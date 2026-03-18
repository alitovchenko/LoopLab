"""Plugin registry introspection for list-components and manifests."""

from __future__ import annotations

from typing import Any, Callable, Type


def ensure_builtin_plugins_loaded() -> None:
    import looplab.model.example_models  # noqa: F401
    import looplab.features.simple  # noqa: F401
    import looplab.controller.policy  # noqa: F401


def _class_qualname(obj: Type[Any] | Callable[..., Any]) -> str:
    if isinstance(obj, type):
        return f"{obj.__module__}.{obj.__qualname__}"
    mod = getattr(obj, "__module__", "")
    name = getattr(obj, "__qualname__", getattr(obj, "__name__", repr(obj)))
    return f"{mod}.{name}" if mod else name


def _first_line_doc(obj: Any) -> str | None:
    d = getattr(obj, "__doc__", None) or ""
    d = d.strip()
    if not d:
        return None
    return d.split("\n")[0].strip()


def _unpack(entry: tuple[Any, ...]) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    if len(entry) == 2:
        return entry[0], entry[1], {}
    return entry[0], entry[1], entry[2]


def build_component_catalog() -> dict[str, dict[str, Any]]:
    """Structured catalog of feature extractors, models, policies."""
    ensure_builtin_plugins_loaded()
    from looplab.features.base import get_feature_extractor_registry
    from looplab.model.base import get_model_registry
    from looplab.controller.policy import get_policy_registry

    def pack(reg: dict[str, tuple]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, entry in sorted(reg.items()):
            cls, defaults, meta = _unpack(entry)
            out[name] = {
                "class": _class_qualname(cls),
                "default_config": dict(defaults),
                "version": meta.get("version"),
                "description": _first_line_doc(cls),
            }
        return out

    return {
        "feature_extractors": pack(get_feature_extractor_registry()),
        "models": pack(get_model_registry()),
        "policies": pack(get_policy_registry()),
    }


def format_component_catalog_text(
    catalog: dict[str, Any],
    *,
    features: bool = True,
    models: bool = True,
    policies: bool = True,
) -> str:
    lines: list[str] = []

    def section(title: str, key: str) -> None:
        data = catalog.get(key, {})
        if not data:
            return
        lines.append(f"{title}:")
        for name, info in data.items():
            ver = info.get("version")
            vstr = f"  [v{ver}]" if ver else ""
            lines.append(f"  {name}{vstr}")
            lines.append(f"    class: {info.get('class', '?')}")
            lines.append(f"    default_config: {info.get('default_config', {})}")
            if info.get("description"):
                lines.append(f"    {info['description']}")
        lines.append("")

    if features:
        section("Feature extractors", "feature_extractors")
    if models:
        section("Models", "models")
    if policies:
        section("Policies", "policies")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
