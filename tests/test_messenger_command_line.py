from transit_core.messenger.adapters.command_line import CommandLineAdapter
from transit_core.messenger.views import Section, Stack, Table


def _adapter() -> CommandLineAdapter:
    return CommandLineAdapter(handler=None)


def test_format_string_passes_through():
    assert _adapter().format("hello") == "hello"


def test_format_table_aligns_columns():
    table = Table(
        headers=["Route", "ETA"],
        rows=[["6", "3 min"], ["NQRW", "10 min"]],
    )
    rendered = _adapter().format(table)
    lines = rendered.split("\n")

    assert lines[0] == "Route  ETA   "
    assert lines[1] == "6      3 min "
    assert lines[2] == "NQRW   10 min"


def test_format_section_stacks_title_subtitle_and_body():
    section = Section(
        title="Arrivals",
        subtitle="for 14 St",
        body="No upcoming arrivals.",
    )
    rendered = _adapter().format(section)
    assert rendered == "Arrivals\nfor 14 St\n\nNo upcoming arrivals."


def test_format_section_with_nested_table():
    section = Section(
        title="Arrivals",
        subtitle="for 14 St",
        body=Table(headers=["Route", "ETA"], rows=[["6", "3 min"]]),
    )
    rendered = _adapter().format(section)
    lines = rendered.split("\n")
    assert lines[:3] == ["Arrivals", "for 14 St", ""]
    assert lines[3] == "Route  ETA  "
    assert lines[4] == "6      3 min"


def test_format_section_without_subtitle_or_body():
    rendered = _adapter().format(Section(title="Done"))
    assert rendered == "Done"


def test_format_stack_joins_children_with_blank_line():
    stack = Stack(items=[Section(title="A"), Section(title="B")])
    rendered = _adapter().format(stack)
    assert rendered == "A\n\nB"


def test_format_section_with_stack_body():
    section = Section(
        title="Top",
        subtitle="sub",
        body=Stack(items=[Section(title="A"), Section(title="B")]),
    )
    rendered = _adapter().format(section)
    assert rendered == "Top\nsub\n\nA\n\nB"
