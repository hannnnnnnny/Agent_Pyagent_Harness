from pyagent.htmltext import html_to_text


def test_title_and_paragraphs() -> None:
    html = "<html><head><title> Docs  Home </title></head><body><p>One</p><p>Two</p></body>"
    assert html_to_text(html) == "# Docs Home\n\nOne\n\nTwo"


def test_scripts_styles_and_head_are_dropped() -> None:
    html = (
        "<head><meta name=x><style>p{}</style></head>"
        "<body><script>steal()</script><p>Visible</p><noscript>x</noscript></body>"
    )
    assert html_to_text(html) == "Visible"


def test_lists_become_bullets() -> None:
    assert html_to_text("<ul><li>a</li><li>b</li></ul>") == "- a\n\n- b"


def test_entities_are_decoded_and_whitespace_collapsed() -> None:
    # &nbsp; decodes to a non-breaking space, which is kept as content.
    assert html_to_text("<p>fish &amp;   chips&nbsp;&lt;3</p>") == "fish & chips\xa0<3"


def test_nested_skipped_tags() -> None:
    assert html_to_text("<svg><g><text>icon</text></g></svg><p>after</p>") == "after"


def test_plain_text_passes_through() -> None:
    assert html_to_text("just text") == "just text"


def test_malformed_html_does_not_raise() -> None:
    assert "text" in html_to_text("<p>text<div><span>more")
