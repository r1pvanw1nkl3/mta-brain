import pytest

from transit_core.messenger.address import NormalizationError, normalize_nyc_address


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("350 5th Ave", "350 5th Ave, New York, NY"),
        ("123 W 42nd St", "123 W 42nd St, New York, NY"),
        ("100 Court St Brooklyn", "100 Court St Brooklyn, New York, NY"),
        ("161 St The Bronx", "161 St The Bronx, New York, NY"),
        ("1 Bay St Staten Island", "1 Bay St Staten Island, New York, NY"),
        ("60-40 68th Rd Ridgewood", "60-40 68th Rd Ridgewood, New York, NY"),
        (
            "60-40 68th Rd Queens Village",
            "60-40 68th Rd Queens Village, New York, NY",
        ),
    ],
)
def test_appends_manhattan_default_when_no_state(raw: str, expected: str):
    assert normalize_nyc_address(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "350 5th Ave, New York, NY",
        "350 5th Ave, New York",
        "350 5th Ave NY",
        "350 5th Ave N.Y.",
        "100 Court St, Brooklyn, NY",
        "60-40 68th Rd, Ridgewood, NY 11385",
        "60-40 68th Rd, Ridgewood, NY 11385-1234",
        "100 Court St, Brooklyn, New York, NY 11201",
    ],
)
def test_idempotent_when_state_already_present(raw: str):
    result = normalize_nyc_address(raw)
    assert isinstance(result, str)
    # Should not double-append a state suffix.
    assert result.lower().count(", new york, ny") <= 1
    assert result.lower().count(", ny,") == 0


@pytest.mark.parametrize(
    "raw",
    [
        "60-40 68th Rd Queens",
        "60-40 68th Rd, Queens",
        "60-40 68th Rd queens",
        "60-40 68th Rd QUEENS",
        "60-40 68th Rd, Queens,",
    ],
)
def test_bare_queens_returns_error(raw: str):
    result = normalize_nyc_address(raw)
    assert isinstance(result, NormalizationError)
    assert "neighborhood" in result.message.lower()


def test_empty_input_returns_error():
    result = normalize_nyc_address("   ")
    assert isinstance(result, NormalizationError)


def test_collapses_whitespace_and_trailing_comma():
    result = normalize_nyc_address("  100   Main   St   Brooklyn  ,  ")
    assert result == "100 Main St Brooklyn, New York, NY"
