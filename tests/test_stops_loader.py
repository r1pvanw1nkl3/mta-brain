from unittest.mock import MagicMock, patch

from services.static_etl.stops_loader import load_entrances


@patch("services.static_etl.stops_loader.psycopg.Connection.connect")
@patch("services.static_etl.stops_loader.requests.get")
@patch("services.static_etl.stops_loader.get_settings")
@patch("services.static_etl.stops_loader.setup_logging")
def test_load_entrances(
    mock_setup_logging, mock_get_settings, mock_requests_get, mock_connect
):
    # Mock settings
    mock_settings = MagicMock()
    mock_settings.etl_log_file_path = "test.log"
    mock_settings.subway_entrances_url = "http://test.url"
    mock_settings.etl_database_url = "postgresql://user:pass@localhost/db"
    mock_get_settings.return_value = mock_settings

    # Mock requests response
    mock_response = MagicMock()
    mock_response.text = (
        "Division,Line,Borough,Stop Name,Complex ID,Constituent Station Name,"
        "Station ID,GTFS Stop ID,Daytime Routes,Entrance Type,Entry Allowed,"
        "Exit Allowed,Entrance Latitude,Entrance Longitude\n"
        "IRT,Lexington,M,Grand Central,1,Grand Central-42 St,1,631,4 5 6,"
        "Stair,YES,YES,40.752,-73.977\n"
        "IND,8th Av,M,42 St-Port Authority,2,42 St-Port Authority Bus Terminal,"
        "2,A27,A C E,Stair,NO,YES,40.757,-73.989"
    )
    mock_requests_get.return_value = mock_response

    # Mock psycopg connection and cursor
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_copy = MagicMock()

    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.copy.return_value.__enter__.return_value = mock_copy

    # Run the function
    load_entrances()

    # Assertions
    mock_get_settings.assert_called_once()
    mock_setup_logging.assert_called_once_with("test.log")
    mock_requests_get.assert_called_once_with("http://test.url")
    mock_response.raise_for_status.assert_called_once()

    mock_connect.assert_called_once()

    # Check that truncate and update were called
    assert mock_cur.execute.call_count == 2
    mock_cur.execute.assert_any_call("TRUNCATE TABLE subway_entrances;")

    # Check that copy.write_row was called twice with parsed data
    assert mock_copy.write_row.call_count == 2

    # Check the first row parsing (YES -> True)
    first_call_args = mock_copy.write_row.call_args_list[0][0][0]
    assert first_call_args[0] == "IRT"
    assert first_call_args[10] is True  # Entry Allowed YES -> True
    assert first_call_args[11] is True  # Exit Allowed YES -> True

    # Check the second row parsing (NO -> False)
    second_call_args = mock_copy.write_row.call_args_list[1][0][0]
    assert second_call_args[10] is False  # Entry Allowed NO -> False

    mock_conn.commit.assert_called_once()
