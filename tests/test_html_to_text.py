import pytest

from jobfinder.adapters import html_to_text


@pytest.mark.parametrize("raw", [None, "", "   ", "<p></p>", "<p> \n </p>"])
def test_empty_inputs_return_empty_string(raw):
    assert html_to_text(raw) == ""


def test_plain_text_is_unchanged():
    assert html_to_text("Hello world") == "Hello world"


def test_tags_are_stripped():
    assert html_to_text("<p>Hello <b>world</b></p>") == "Hello\nworld"


def test_block_elements_are_separated_by_newlines():
    raw = "<p>First paragraph</p><p>Second paragraph</p>"
    assert html_to_text(raw) == "First paragraph\nSecond paragraph"


def test_list_items_are_separated_by_newlines():
    assert html_to_text("<ul><li>one</li><li>two</li></ul>") == "one\ntwo"


def test_line_breaks_become_newlines():
    assert html_to_text("line one<br>line two") == "line one\nline two"


def test_surrounding_whitespace_is_stripped_from_each_fragment():
    assert html_to_text("<p>  padded  </p>") == "padded"


def test_non_breaking_space_entity_becomes_regular_space():
    result = html_to_text("<p>foo&nbsp;bar</p>")
    assert result == "foo bar"
    assert "\xa0" not in result


def test_raw_non_breaking_space_character_becomes_regular_space():
    assert html_to_text("<p>foo\xa0bar</p>") == "foo bar"


def test_real_world_lever_list_content():
    raw = (
        "<p><strong>Flex your schedule.</strong> Work from home up to 2 days.</p>\n"
        "<p><strong>Eat well.</strong>&nbsp;Lunch card, 50% on us.</p>"
    )
    assert html_to_text(raw) == (
        "Flex your schedule.\n"
        "Work from home up to 2 days.\n"
        "Eat well.\n"
        "Lunch card, 50% on us."
    )


class TestUnescape:
    """Greenhouse returns HTML that is escaped a second time."""

    ESCAPED = "&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;"

    def test_without_unescape_escaped_markup_stays_as_literal_text(self):
        assert html_to_text(self.ESCAPED) == "<p>Hello <b>world</b></p>"

    def test_with_unescape_escaped_markup_is_parsed(self):
        assert html_to_text(self.ESCAPED, unescape=True) == "Hello\nworld"

    def test_unescape_is_disabled_by_default(self):
        assert html_to_text(self.ESCAPED) != html_to_text(self.ESCAPED, unescape=True)

    def test_unescape_does_not_break_regular_html(self):
        assert html_to_text("<p>Hello</p>", unescape=True) == "Hello"

    def test_unescape_with_none_returns_empty_string(self):
        assert html_to_text(None, unescape=True) == ""

    def test_escaped_nbsp_is_normalised(self):
        assert (
            html_to_text("&lt;p&gt;foo&amp;nbsp;bar&lt;/p&gt;", unescape=True)
            == "foo bar"
        )
