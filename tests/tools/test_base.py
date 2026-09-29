from pathlib import Path
from typing import Any

import pytest

from pyagent.safety.verdict import Verdict
from pyagent.tools.base import Risk, Tool, ToolContext


class Echo(Tool):
    name = "echo"
    description = "Echo the text back."
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        return str(args["text"])


def test_spec_matches_api_shape() -> None:
    assert Echo().spec() == {
        "name": "echo",
        "description": "Echo the text back.",
        "input_schema": Echo.input_schema,
    }


def test_default_risk_is_read() -> None:
    assert Echo.risk is Risk.READ


def test_run_receives_context(tmp_path: Path) -> None:
    assert Echo().run({"text": "hi"}, ToolContext.for_root(tmp_path)) == "hi"


def test_default_assessment_allows(tmp_path: Path) -> None:
    assessment = Echo().assess({"text": "x"}, ToolContext.for_root(tmp_path))
    assert assessment.verdict is Verdict.ALLOW


def test_tool_is_abstract() -> None:
    with pytest.raises(TypeError):
        Tool()  # type: ignore[abstract]
