"""A small JSON Schema validator for tool inputs.

Model output is untrusted, so every tool input is validated before a tool
runs. Only the subset of JSON Schema that tool definitions use is supported;
unsupported keywords are rejected at definition time rather than ignored.
"""

from __future__ import annotations

from typing import Any

from pyagent.errors import ToolInputError

_TYPES: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list,),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "null": (type(None),),
}


def _check_type(value: Any, expected: str, path: str) -> None:
    # bool is a subclass of int in Python but not an integer in JSON.
    if expected in {"integer", "number"} and isinstance(value, bool):
        raise ToolInputError(f"{path}: expected {expected}, got boolean")
    if not isinstance(value, _TYPES[expected]):
        raise ToolInputError(f"{path}: expected {expected}, got {type(value).__name__}")


def _check_string(value: str, schema: dict[str, Any], path: str) -> None:
    if "minLength" in schema and len(value) < schema["minLength"]:
        raise ToolInputError(f"{path}: shorter than {schema['minLength']} characters")
    if "maxLength" in schema and len(value) > schema["maxLength"]:
        raise ToolInputError(f"{path}: longer than {schema['maxLength']} characters")


def _check_number(value: float, schema: dict[str, Any], path: str) -> None:
    if "minimum" in schema and value < schema["minimum"]:
        raise ToolInputError(f"{path}: must be >= {schema['minimum']}")
    if "maximum" in schema and value > schema["maximum"]:
        raise ToolInputError(f"{path}: must be <= {schema['maximum']}")


def _check_object(value: dict[str, Any], schema: dict[str, Any], path: str) -> None:
    properties: dict[str, Any] = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in value:
            raise ToolInputError(f"{path}: missing required property {name!r}")
    if schema.get("additionalProperties") is False:
        extra = sorted(set(value) - set(properties))
        if extra:
            raise ToolInputError(f"{path}: unexpected properties {extra}")
    for name, sub in properties.items():
        if name in value:
            validate(value[name], sub, f"{path}.{name}")


def _check_array(value: list[Any], schema: dict[str, Any], path: str) -> None:
    if "maxItems" in schema and len(value) > schema["maxItems"]:
        raise ToolInputError(f"{path}: more than {schema['maxItems']} items")
    if "items" in schema:
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")


def validate(value: Any, schema: dict[str, Any], path: str = "input") -> None:
    """Raise :class:`ToolInputError` if ``value`` does not satisfy ``schema``."""
    if "enum" in schema and value not in schema["enum"]:
        raise ToolInputError(f"{path}: must be one of {schema['enum']}")
    expected = schema.get("type")
    if expected is None:
        return
    _check_type(value, expected, path)
    if expected == "string":
        _check_string(value, schema, path)
    elif expected in {"integer", "number"}:
        _check_number(value, schema, path)
    elif expected == "object":
        _check_object(value, schema, path)
    elif expected == "array":
        _check_array(value, schema, path)
