"""Adapt JSON Schema to Gemini's output grammar without changing caller data."""

from typing import Any


def simplify_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    def simplify(value: Any) -> Any:
        if isinstance(value, list):
            return [simplify(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, item in value.items():
            if key in {"title", "minLength", "maxLength", "minItems", "maxItems"}:
                continue
            if key in {"properties", "$defs"}:
                result[key] = {name: simplify(child) for name, child in item.items()}
            else:
                result[key] = simplify(item)
        return result

    return simplify(schema)
