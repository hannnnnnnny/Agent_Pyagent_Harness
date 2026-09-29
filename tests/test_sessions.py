from pathlib import Path

import pytest

from pyagent.messages import Conversation
from pyagent.providers.scripted import text_turn
from pyagent.sessions import SessionError, SessionStore, new_session_id, session_summary


def _conversation() -> Conversation:
    convo = Conversation()
    convo.add_user_text("hello")
    convo.add_assistant(text_turn("hi there"))
    return convo


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


def test_new_ids_are_valid_and_unique(store: SessionStore) -> None:
    ids = {new_session_id() for _ in range(50)}
    assert len(ids) == 50
    for session_id in ids:
        store.save(session_id, Conversation(), title="t", model="m")


def test_round_trip(store: SessionStore) -> None:
    sid = new_session_id()
    store.save(sid, _conversation(), title="greeting", model="claude-opus-5-5")
    assert store.load(sid).messages == _conversation().messages


def test_list_is_newest_first_with_metadata(store: SessionStore) -> None:
    first, second = new_session_id(), new_session_id()
    store.save(first, _conversation(), title="first", model="m")
    store.save(second, Conversation(), title="second", model="m")
    store.save(first, _conversation(), title="first again", model="m")
    infos = store.list_sessions()
    assert {i.id for i in infos} == {first, second}
    info = next(i for i in infos if i.id == first)
    assert info.title == "first again"
    assert info.messages == 2
    assert info.created <= info.updated
    assert first in session_summary(info)


@pytest.mark.parametrize("bad", ["../../etc/passwd", "ABCDEF123456", "short", "a" * 13, ""])
def test_ids_are_validated(store: SessionStore, bad: str) -> None:
    with pytest.raises(SessionError, match="invalid session id"):
        store.load(bad)


def test_missing_session(store: SessionStore) -> None:
    with pytest.raises(SessionError, match="no session"):
        store.load(new_session_id())


def test_corrupt_session(store: SessionStore) -> None:
    sid = new_session_id()
    store.directory.mkdir(parents=True)
    (store.directory / f"{sid}.json").write_text('{"id": "x", "messages": [{"role": "evil"}]}')
    with pytest.raises(SessionError, match="corrupt"):
        store.load(sid)


def test_list_skips_unreadable_files(store: SessionStore) -> None:
    store.directory.mkdir(parents=True)
    (store.directory / "junk.json").write_text("not json")
    (store.directory / "list.json").write_text("[1, 2]")
    assert store.list_sessions() == []


def test_list_without_directory(store: SessionStore) -> None:
    assert store.list_sessions() == []


def test_long_titles_are_clipped(store: SessionStore) -> None:
    sid = new_session_id()
    store.save(sid, Conversation(), title="x" * 1000, model="m")
    assert len(store.list_sessions()[0].title) == 200
