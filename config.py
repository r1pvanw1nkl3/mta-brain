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

_paths = _settings.get("paths", {})
LOG_FILE_PATH = _paths.get("log_file", "logs/app.log")

