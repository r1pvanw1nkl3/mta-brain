import os
import json
from dotenv import load_dotenv
import logging

try:
    with open("settings.json") as f:
        _settings = json.load(f)
except FileNotFoundError:
    print("FATAL ERROR: settings.json not found.")
    _settings = {}

load_dotenv()
DB_URL = os.getenv("DB_URL", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "gtfs")

_feed_urls = _settings.get("gtfs_feed_urls", {})
GTFS_STATIC_URL = _feed_urls.get("static")
GTFS_SUPPLEMENTED_URL = _feed_urls.get("supplemented")

_paths = _settings.get("paths", {})
LOG_FILE_PATH = _paths.get("log_path", "logs/app.log")
ETL_LOG_FILE_PATH = _paths.get("etl_log_path", "logs/etl.log")
GTFS_STATIC_PATH = _paths.get("gtfs_static", "gtfs_static")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
