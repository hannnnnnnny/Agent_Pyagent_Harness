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
