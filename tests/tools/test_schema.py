import re

import pytest

from pyagent.errors import ToolInputError
from pyagent.tools.schema import check_schema, validate

SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "minLength": 1, "maxLength": 10},
        "limit": {"type": "integer", "minimum": 1, "maximum": 5},
        "mode": {"type": "string", "enum": ["a", "b"]},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
        "ratio": {"type": "number"},
    },
    "required": ["path"],
    "additionalProperties": False,
}


def test_valid_input_passes() -> None:
    validate({"path": "x", "limit": 3, "mode": "a", "tags": ["t"], "ratio": 0.5}, SCHEMA)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({}, "missing required property 'path'"),
        ({"path": ""}, "shorter than"),
        ({"path": "x" * 11}, "longer than"),
        ({"path": "x", "limit": 0}, ">= 1"),
        ({"path": "x", "limit": 6}, "<= 5"),
        ({"path": "x", "limit": True}, "got boolean"),
        ({"path": "x", "limit": "3"}, "expected integer"),
        ({"path": "x", "mode": "c"}, "must be one of"),
        ({"path": "x", "tags": ["a", "b", "c"]}, "more than 2 items"),
        ({"path": "x", "tags": [1]}, "input.tags[0]"),
        ({"path": "x", "evil": 1}, "unexpected properties ['evil']"),
        ([], "expected object"),
    ],
)
def test_invalid_input_is_rejected(value: object, message: str) -> None:
    with pytest.raises(ToolInputError, match=re.escape(message)):
        validate(value, SCHEMA)


def test_integer_accepted_for_number() -> None:
    validate({"path": "x", "ratio": 2}, SCHEMA)


def test_check_schema_accepts_supported_schema() -> None:
    check_schema(SCHEMA)


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "string", "pattern": ".*"},
        {"type": "object", "properties": {"a": {"type": "wat"}}},
        {"type": "array", "items": {"oneOf": []}},
    ],
)
def test_check_schema_rejects_unsupported(schema: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        check_schema(schema)
