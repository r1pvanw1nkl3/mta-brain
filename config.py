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

#_feed_urls = _settings.get("feed_urls", {})
#GTFS_STATIC_URL = _feed_urls.get("static")
#GTFS_SUPPLEMENTED_URL = _feed_urls.urls.get("supplemented")

_log_paths = _settings.get("log_paths", {})
LOG_FILE_PATH = _log_paths.get("log_path", "logs/app.log")
ETL_LOG_FILE_PATH = _log_paths.get("etl_log_path", "logs/etl.log")

