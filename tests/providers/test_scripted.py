import pytest

from pyagent.errors import ProviderError
from pyagent.providers.base import ModelRequest
from pyagent.providers.scripted import ScriptedProvider, text_turn, tool_turn

REQUEST = ModelRequest(system="s", messages=[{"role": "user", "content": "hi"}])


def test_text_turn_shape() -> None:
    turn = text_turn("done")
    assert turn.text == "done"
    assert turn.stop_reason == "end_turn"
    assert turn.tool_calls == []


def test_tool_turn_has_unique_ids() -> None:
    turn = tool_turn(("read_file", {"path": "a"}), ("glob", {"pattern": "*"}), text="Looking.")
    assert turn.stop_reason == "tool_use"
    assert turn.text == "Looking."
    ids = [c.id for c in turn.tool_calls]
    assert len(set(ids)) == 2
    assert [c.name for c in turn.tool_calls] == ["read_file", "glob"]


def test_scripted_provider_replays_in_order_and_records() -> None:
    provider = ScriptedProvider([text_turn("one"), text_turn("two")])
    assert provider.complete(REQUEST).text == "one"
    assert provider.complete(REQUEST).text == "two"
    assert provider.requests == [REQUEST, REQUEST]


def test_scripted_provider_fails_loudly_when_exhausted() -> None:
    with pytest.raises(ProviderError):
        ScriptedProvider([]).complete(REQUEST)
