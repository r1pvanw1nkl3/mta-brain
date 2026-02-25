import io
import zipfile
from unittest.mock import MagicMock, call, patch

import pytest

from services.static_etl import db_loader, etl_runner, gtfs_download, gtfs_parser

# --- Tests for db_loader.py ---


def test_truncate_tables():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    db_loader.truncate_tables(mock_conn, schema="test_schema")

    # Verify execute was called with a Composed object that represents the right SQL
    args, _ = mock_cursor.execute.call_args
    sql_obj = args[0]
    sql_str = sql_obj.as_string(None)

    assert "TRUNCATE" in sql_str
    assert '"test_schema"."agency"' in sql_str
    assert "CASCADE" in sql_str


def test_load_table_success():
    mock_cursor = MagicMock()
    mock_copy = MagicMock()
    mock_cursor.copy.return_value.__enter__.return_value = mock_copy

    # Create dummy CSV data
    csv_content = "stop_id,stop_name\n1,Station A\n2,Station B\n"
    file_obj = io.StringIO(csv_content)

    db_loader.load_table(mock_cursor, "stops", file_obj, "test_schema")

    # Verify COPY command
    args, _ = mock_cursor.copy.call_args
    sql_obj = args[0]
    sql_str = sql_obj.as_string(None)

    assert 'COPY "test_schema"."stops"' in sql_str
    assert '"stop_id", "stop_name"' in sql_str
    assert "FROM STDIN" in sql_str

    # Verify data writing - logic in db_loader reads in chunks
    assert mock_copy.write.called


def test_load_table_unsafe_column():
    mock_cursor = MagicMock()
    file_obj = io.StringIO("unsafe;drop,stop_name\n1,A\n")

    with pytest.raises(ValueError, match="Unsafe column name"):
        db_loader.load_table(mock_cursor, "stops", file_obj, "public")


def test_load_all():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Mock data map with one table
    mock_file = io.StringIO("h1\nv1")
    data_map = {"stops": mock_file}

    # Patch truncate and load_table to verify orchestration
    with (
        patch("services.static_etl.db_loader.truncate_tables") as mock_trunc,
        patch("services.static_etl.db_loader.load_table") as mock_load,
    ):
        db_loader.load_all(mock_conn, data_map, "public")

        mock_conn.transaction.assert_called_once()
        mock_trunc.assert_called_once_with(mock_conn, "public")
        mock_load.assert_called_once_with(mock_cursor, "stops", mock_file, "public")


# --- Tests for gtfs_download.py ---


def test_retrieve_feed_success(mock_env_vars, tmp_path):
    # Mock settings to point to a temp dir for download
    # patch get_settings in the module where it is used or globally
    with (
        patch("services.static_etl.gtfs_download.get_settings") as mock_get_settings,
        patch("urllib.request.urlretrieve") as mock_retrieve,
    ):
        # Configure the mock settings object
        mock_settings = mock_get_settings.return_value
        mock_settings.project_root = str(tmp_path)
        mock_settings.gtfs_static_path = "gtfs_static"

        # Create a dummy file so os.path.getsize works
        target_dir = tmp_path / "gtfs_static"
        target_dir.mkdir(parents=True)
        (target_dir / "test_feed.zip").touch()

        path = gtfs_download._retrieve_feed(
            "test_feed.zip", "http://example.com/feed.zip"
        )

        expected_path = str(target_dir / "test_feed.zip")
        assert path == expected_path
        mock_retrieve.assert_called_once_with(
            "http://example.com/feed.zip", expected_path
        )


def test_retrieve_feed_failure(mock_env_vars):
    with patch("urllib.request.urlretrieve", side_effect=OSError("Disk full")):
        path = gtfs_download._retrieve_feed("test.zip", "http://bad.com")
        assert path is None


# --- Tests for gtfs_parser.py ---


def test_process_gtfs_zip():
    # Create a real in-memory zip file
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w") as zf:
        zf.writestr("stops.txt", "stop_id,stop_name\n1,A")
        zf.writestr("ignored.pdf", "junk")
    mem_zip.seek(0)

    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.connection.return_value.__enter__.return_value = mock_conn

    # Create the real ZipFile object BEFORE patching zipfile.ZipFile
    real_zip = zipfile.ZipFile(mem_zip, "r")

    with (
        patch("zipfile.ZipFile") as MockZip,
        patch("services.static_etl.db_loader.load_all") as mock_load_all,
    ):
        # Make the mock context manager return the real ZipFile
        MockZip.return_value.__enter__.return_value = real_zip

        gtfs_parser.process_gtfs_zip(mock_pool, "/fake/path/test.zip", "public")

        # Verify load_all was called
        assert mock_load_all.called
        args = mock_load_all.call_args
        conn_arg, map_arg, schema_arg = args[0]

        assert conn_arg == mock_conn
        assert schema_arg == "public"
        assert "stops" in map_arg
        assert "ignored" not in map_arg  # Only .txt files


# --- Tests for etl_runner.py ---


def test_run_reload_all(mock_env_vars):
    with (
        patch("services.static_etl.etl_runner.get_regular_feed") as mock_get_reg,
        patch("services.static_etl.etl_runner.get_supplemented_feed") as mock_get_supp,
        patch("services.static_etl.etl_runner.process_gtfs_zip") as mock_process,
        patch("services.static_etl.etl_runner.create_db_pool") as mock_create_pool,
        patch("services.static_etl.etl_runner.wait_for_db"),
    ):
        mock_get_reg.return_value = "/tmp/reg.zip"
        mock_get_supp.return_value = "/tmp/supp.zip"

        etl_runner.run_reload(all=True)

        assert mock_get_reg.called
        assert mock_get_supp.called
        assert mock_process.call_count == 2  # Once for reg, once for supp
        assert mock_process.call_args_list == [
            call(
                mock_create_pool.return_value.__enter__.return_value,
                "/tmp/reg.zip",
                schema="public",
            ),
            call(
                mock_create_pool.return_value.__enter__.return_value,
                "/tmp/supp.zip",
                schema="supplemented",
            ),
        ]


def test_run_reload_supplemented_only(mock_env_vars):
    with (
        patch("services.static_etl.etl_runner.get_regular_feed"),
        patch("services.static_etl.etl_runner.get_supplemented_feed") as mock_get_supp,
        patch("services.static_etl.etl_runner.process_gtfs_zip") as mock_process,
        patch("services.static_etl.etl_runner.create_db_pool"),
        patch("services.static_etl.etl_runner.wait_for_db"),
    ):
        etl_runner.run_reload(all=False)

        assert mock_get_supp.called
        assert mock_process.call_count == 1


def test_reload_all_wrapper():
    with patch("services.static_etl.etl_runner.run_reload") as mock_run:
        etl_runner.reload_all()
        mock_run.assert_called_once_with(True)


def test_run_reload_download_exception():
    with patch(
        "services.static_etl.etl_runner.get_supplemented_feed",
        side_effect=Exception("Download failed"),
    ):
        # Should not raise exception, just log and return
        etl_runner.run_reload(all=False)


def test_run_reload_process_exception():
    with (
        patch("services.static_etl.etl_runner.get_supplemented_feed") as mock_get,
        patch(
            "services.static_etl.etl_runner.create_db_pool",
            side_effect=Exception("Pool failed"),
        ),
    ):
        mock_get.return_value = "file.zip"
        # Should not raise exception
        etl_runner.run_reload(all=False)


def test_get_regular_feed():
    with patch("services.static_etl.gtfs_download._retrieve_feed") as mock_retrieve:
        gtfs_download.get_regular_feed()
        mock_retrieve.assert_called_once()


def test_get_supplemented_feed():
    with patch("services.static_etl.gtfs_download._retrieve_feed") as mock_retrieve:
        gtfs_download.get_supplemented_feed()
        mock_retrieve.assert_called_once()
