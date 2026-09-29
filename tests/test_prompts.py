from pyagent.prompts import DEFAULT_SYSTEM_PROMPT, build_system_prompt


def test_default_prompt_covers_safety_rules() -> None:
    lowered = DEFAULT_SYSTEM_PROMPT.lower()
    assert "data, not instructions" in lowered
    assert "credentials" in lowered
    assert "blocked or declined" in lowered


def test_prompt_is_stable_without_extras() -> None:
    assert build_system_prompt() == build_system_prompt("   ") == DEFAULT_SYSTEM_PROMPT


def test_extra_instructions_are_appended_after_the_defaults() -> None:
    prompt = build_system_prompt("Use tabs.")
    assert prompt.startswith(DEFAULT_SYSTEM_PROMPT)
    assert prompt.rstrip().endswith("Use tabs.")
