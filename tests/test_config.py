from pathlib import Path

from pydantic_settings import SettingsConfigDict

from transit_core.config import Settings, get_settings


def test_database_url_generation(mock_env_vars):
    """
    Test that the ETL database URL is constructed correctly
    from the individual components.
    """

    settings = get_settings()

    assert settings.db_host == "test-host"

    url = settings.etl_database_url
    assert "user=test_user" in url
    assert "password=test_pass" in url
    assert "port=9999" in url


def test_missing_env_variable(monkeypatch, mock_env_vars):
    # Testing that a TRULY required field (if any) raises ValidationError.
    # Since all current fields have defaults or are optional, we might need
    # a different approach if we want to test Pydantic validation.
    # For now, let's just ensure it doesn't crash when optional fields are missing.
    monkeypatch.delenv("APP_DB_PASSWORD", raising=False)

    class NoEnvSettings(Settings):
        model_config = SettingsConfigDict(env_file=None)

    # This should now succeed because app_db_password is str | None = None
    settings = NoEnvSettings()
    assert settings.app_db_password is None


def test_project_paths_resolution(mock_env_vars):
    """
    Verify that paths are resolving to the project root,
    not inside the src directory.
    """

    class NoEnvSettings(Settings):
        model_config = SettingsConfigDict(env_file=None)

    settings = NoEnvSettings()

    # Convert to Path objects for easier comparison
    root = Path(settings.project_root)

    # Ensure the root contains our pyproject.toml (the ultimate proof of 'root')
    assert (root / "pyproject.toml").exists()

    # Ensure logs/ and gtfs_static/ are being pointed to correctly
    # If project_root is wrong, these would likely be absolute paths pointing
    # somewhere inside /src/transit_core/
    assert "src" not in settings.gtfs_static_path
    assert "src" not in settings.log_file_path
