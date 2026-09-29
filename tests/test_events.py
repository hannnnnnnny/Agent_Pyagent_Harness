from pyagent.events import Event, EventBus


def test_emit_delivers_to_all_subscribers() -> None:
    bus = EventBus()
    seen: list[Event] = []
    bus.subscribe(seen.append)
    bus.subscribe(seen.append)
    event = bus.emit("turn_started", turn=1)
    assert seen == [event, event]
    assert event.data == {"turn": 1}


def test_failing_handler_does_not_stop_others() -> None:
    bus = EventBus()
    seen: list[Event] = []

    def broken(_: Event) -> None:
        raise RuntimeError("frontend crashed")

    bus.subscribe(broken)
    bus.subscribe(seen.append)
    bus.emit("x")
    assert len(seen) == 1
    assert isinstance(bus.handler_errors[0], RuntimeError)
