import io
import json

from pyagent.agent import RunResult
from pyagent.cli.render import ConsoleRenderer, format_result, result_to_dict
from pyagent.events import EventBus
from pyagent.usage import Usage


def _render(*events: tuple[str, dict[str, object]], verbose: bool = False) -> str:
    out = io.StringIO()
    bus = EventBus()
    bus.subscribe(ConsoleRenderer(out, verbose=verbose))
    for kind, data in events:
        bus.emit(kind, **data)
    return out.getvalue()


def test_tool_lifecycle_is_rendered() -> None:
    text = _render(
        ("tool_started", {"tool": "read_file", "input": {"path": "a.py"}}),
        ("tool_finished", {"tool": "read_file", "is_error": False, "output": "1\tprint()"}),
        ("tool_finished", {"tool": "grep", "is_error": True, "output": "bad regex"}),
    )
    assert '> read_file {"path": "a.py"}' in text
    assert "[ok] 1 print()" in text
    assert "[error] bad regex" in text


def test_long_output_is_previewed() -> None:
    text = _render(("tool_finished", {"is_error": False, "output": "x" * 5000}))
    assert len(text) < 200
    assert text.rstrip().endswith("...")


def test_verbose_shows_more_output() -> None:
    text = _render(("tool_finished", {"is_error": False, "output": "x" * 5000}), verbose=True)
    assert 900 < len(text) < 1100


def test_blocked_and_injection_warnings() -> None:
    text = _render(
        ("action_blocked", {"reason": "privilege escalation via sudo"}),
        ("injection_suspected", {"phrase": "ignore previous instructions"}),
    )
    assert "[blocked] privilege escalation via sudo" in text
    assert "possible prompt injection" in text


def test_interim_model_text_shown_only_with_tool_calls() -> None:
    assert "Checking" in _render(
        ("model_responded", {"text": "Checking files.", "tool_calls": ["glob"]})
    )
    assert _render(("model_responded", {"text": "Final.", "tool_calls": []})) == ""


def test_unknown_events_are_ignored() -> None:
    assert _render(("something_new", {})) == ""


def test_format_result() -> None:
    result = RunResult("Done!", "completed", 3, Usage(100, 50), cost_usd=0.0123)
    assert format_result(result) == "Done!\n[completed] 3 turns, 150 tokens, ~$0.0123"


def test_format_result_with_detail_and_no_text() -> None:
    result = RunResult("", "budget", 2, Usage(), detail="reached the limit of 2 turns")
    assert format_result(result) == "[budget] 2 turns, 0 tokens - reached the limit of 2 turns"


def test_result_to_dict_is_json_serializable() -> None:
    result = RunResult("Done", "completed", 2, Usage(10, 5), cost_usd=0.5, detail="")
    data = result_to_dict(result, "abc123abc123")
    assert json.loads(json.dumps(data)) == {
        "stop": "completed",
        "ok": True,
        "text": "Done",
        "turns": 2,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
        "cost_usd": 0.5,
        "detail": "",
        "session": "abc123abc123",
    }
