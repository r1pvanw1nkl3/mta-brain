from urllib import request
from urllib.error import URLError, HTTPError
from config import settings
import logging
import os

logger = logging.getLogger(__name__)

def get_regular_feed():
    """Downloads the regular GTFS feed."""
    _retrieve_feed("gtfs_subway.zip", settings.gtfs_static_url)

def get_supplemented_feed():
    """Downloads the supplemented GTFS feed."""
    _retrieve_feed("gtfs_supplemented.zip", settings.gtfs_supplemented_url)

def _retrieve_feed(file_name: str, url: str):
    """
    Retrieves a feed from a URL and saves it to the static GTFS path.
    """
    logger.info(f"Downloading feed from {url}")
    try:
        target_dir = os.path.join(settings.project_root, settings.gtfs_static_path)
        os.makedirs(target_dir, exist_ok=True)
        request.urlretrieve(url, os.path.join(target_dir, file_name))
        logger.info(f"Successfully downloaded {file_name} from {url}")
    except (HTTPError, URLError) as e:
        logger.error(f"Failed to download feed from {url}. Error: {e}")
    except OSError as e:
        logger.error(f"File system error: {e}")
