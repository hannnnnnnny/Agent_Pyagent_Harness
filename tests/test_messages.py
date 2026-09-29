import pytest

from pyagent.messages import Conversation, ModelResponse, ToolCall, ToolResult
from pyagent.usage import Usage


def _response() -> ModelResponse:
    return ModelResponse(
        content=[
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "text", "text": "Let me look. "},
            {"type": "tool_use", "id": "t1", "name": "read_file", "input": {"path": "a"}},
            {"type": "text", "text": "Done."},
        ],
        stop_reason="tool_use",
        model="claude-opus-5-5",
        usage=Usage(5, 7),
    )


def test_tool_result_block_omits_is_error_when_false() -> None:
    assert "is_error" not in ToolResult("t1", "ok").to_block()


def test_tool_result_block_marks_errors() -> None:
    assert ToolResult("t1", "boom", is_error=True).to_block()["is_error"] is True


def test_response_text_joins_text_blocks_only() -> None:
    assert _response().text == "Let me look. Done."


def test_response_extracts_tool_calls() -> None:
    assert _response().tool_calls == [ToolCall("t1", "read_file", {"path": "a"})]


def test_conversation_preserves_assistant_blocks_verbatim() -> None:
    convo = Conversation()
    convo.add_user_text("hi")
    convo.add_assistant(_response())
    assert convo.messages[1]["content"] == _response().content
    assert convo.last_role == "assistant"


def test_tool_results_share_one_user_message() -> None:
    convo = Conversation()
    convo.add_tool_results([ToolResult("a", "1"), ToolResult("b", "2")])
    assert len(convo) == 1
    assert [b["tool_use_id"] for b in convo.messages[0]["content"]] == ["a", "b"]


def test_empty_tool_results_rejected() -> None:
    with pytest.raises(ValueError):
        Conversation().add_tool_results([])


def test_messages_property_is_a_copy() -> None:
    convo = Conversation()
    convo.add_user_text("hi")
    convo.messages.clear()
    assert len(convo) == 1


def test_empty_conversation_has_no_last_role() -> None:
    assert Conversation().last_role is None


def test_conversation_json_round_trip() -> None:
    convo = Conversation()
    convo.add_user_text("héllo")
    convo.add_assistant(_response())
    restored = Conversation.from_json(convo.to_json())
    assert restored.messages == convo.messages


@pytest.mark.parametrize("payload", ['{"role": "user"}', '[{"role": "hacker"}]', "[1]"])
def test_conversation_from_json_rejects_malformed_payloads(payload: str) -> None:
    with pytest.raises(ValueError):
        Conversation.from_json(payload)
