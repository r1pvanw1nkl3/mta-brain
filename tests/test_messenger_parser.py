from transit_core.messenger.parser import ParsedCommand, ParseError, parse_message


def test_empty_input_returns_none():
    assert parse_message("") is None


def test_non_command_returns_none():
    assert parse_message("hello world") is None


def test_arrivals_with_stop_id_returns_parsed_command():
    result = parse_message("!arrivals 635N")
    assert result == ParsedCommand("arrivals", {"stop_id": "635N"})


def test_arrivals_without_arg_returns_parse_error():
    result = parse_message("!arrivals")
    assert isinstance(result, ParseError)
    assert "stop_id" in result.message


def test_unknown_command_returns_parse_error():
    result = parse_message("!nope")
    assert isinstance(result, ParseError)
    assert "nope" in result.message
