from unittest.mock import patch

from transit_core.api.cli import main


@patch("transit_core.api.cli.uvicorn.run")
def test_api_cli_main(mock_run):
    main()
    mock_run.assert_called_once_with(
        "transit_core.api.main:app", host="127.0.0.1", port=8000, reload=True
    )
