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


def test_search_with_query_returns_parsed_command():
    result = parse_message("!search union square")
    assert result == ParsedCommand("search", {"search_string": "union square"})


def test_search_without_arg_returns_parse_error():
    result = parse_message("!search")
    assert isinstance(result, ParseError)
    assert "search" in result.message.lower()


def test_nearby_with_address_returns_parsed_command():
    result = parse_message("!nearby 350 5th Ave")
    assert result == ParsedCommand("nearby", {"address": "350 5th Ave"})


def test_nearby_collapses_internal_whitespace():
    result = parse_message("!nearby  100   Court  St  Brooklyn")
    assert result == ParsedCommand("nearby", {"address": "100 Court St Brooklyn"})


def test_nearby_without_arg_returns_parse_error():
    result = parse_message("!nearby")
    assert isinstance(result, ParseError)
    assert "nearby" in result.message.lower() or "address" in result.message.lower()


def test_planner_with_address_returns_parsed_command():
    result = parse_message("!planner 350 5th Ave")
    assert result == ParsedCommand("planner", {"address": "350 5th Ave"})


def test_planner_without_arg_returns_parse_error():
    result = parse_message("!planner")
    assert isinstance(result, ParseError)
    assert "planner" in result.message.lower() or "address" in result.message.lower()
