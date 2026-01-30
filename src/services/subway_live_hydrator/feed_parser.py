import logging
import time

import requests
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from pydantic import ValidationError

import transit_core.core.models as models
import transit_core.core.protos.gtfs_realtime_pb2 as pb
from transit_core.config import get_settings

logger = logging.getLogger(__name__)


def fetch_raw_feed(feed_url: str):
    cfg = get_settings()
    for attempt in range(0, cfg.gtfs_realtime_retries):
        try:
            logger.info(f"Attempting to fetch feed {feed_url}")
            response = requests.get(feed_url, timeout=cfg.gtfs_timeout)
            response.raise_for_status()
            logger.info(
                f"""Fetched feed {feed_url}. Status: {response.status_code},
                Size: {len(response.content)} bytes"""
            )
            feed = pb.FeedMessage()
            feed.ParseFromString(response.content)
            feed_dict = MessageToDict(
                feed, preserving_proto_field_name=True, use_integers_for_enums=True
            )
            entity_count = len(feed_dict.get("entity", []))
            logger.info(f"Parsed feed {feed_url} with {entity_count} entities")
            return feed_dict
        except (requests.RequestException, DecodeError, requests.HTTPError) as e:
            error_type = type(e).__name__
            logger.error(f"Error on attempt {attempt + 1}: {error_type}")
            if attempt < cfg.gtfs_realtime_retries:
                time.sleep(cfg.gtfs_retry_delay)
            else:
                raise e
    logger.error(
        f"Unable to fetch feed {feed_url} after {cfg.gtfs_realtime_retries} attempts"
    )
    return None


def validate_feed(feed_dict):
    logger.info("Attempting to validate feed.")
    try:
        return models.Feed.model_validate(feed_dict)
    except ValidationError as e:
        logger.error(f"Feed validation failed: {e}")
        raise e
