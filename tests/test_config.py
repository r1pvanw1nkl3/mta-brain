import os
from pathlib import Path
import pytest
from pydantic import ValidationError
from transit_core.config import Settings, get_settings

def test_database_url_generation():
    """
    Test that the ETL database URL is constructed correctly
    from the individual components.
    """

    settings = get_settings()

    expected_url = "host='test-host' port='9999' dbname='test_db' user='test_user' password='test_pass'"
    
    assert settings.db_host == "test-host"

    url = settings.etl_database_url
    assert "user=test_user" in url
    assert "password=test_pass" in url
    assert "port=9999" in url

def test_missing_env_variable(monkeypatch):
    monkeypatch.delenv("ETL_DB_PASSWORD", raising=False)
    monkeypatch.delenv("APP_DB_PASSWORD", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "etl_db_password" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)

def test_project_paths_resolution():
    """
    Verify that paths are resolving to the project root,
    not inside the src directory.
    """
    settings = Settings(_env_file=None)
    
    # Convert to Path objects for easier comparison
    root = Path(settings.project_root)
    static_dir = Path(settings.gtfs_static_path)
    
    # Ensure the root contains our pyproject.toml (the ultimate proof of 'root')
    assert (root / "pyproject.toml").exists()
    
    # Ensure logs/ and gtfs_static/ are being pointed to correctly
    # If project_root is wrong, these would likely be absolute paths pointing 
    # somewhere inside /src/transit_core/
    assert "src" not in settings.gtfs_static_path
    assert "src" not in settings.log_file_path