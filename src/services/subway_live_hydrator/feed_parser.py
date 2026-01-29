import logging
import time

import requests
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError

import transit_core.core.models as models
import transit_core.core.protos.gtfs_realtime_pb2 as pb
from transit_core.config import get_settings

logger = logging.getLogger(__name__)


def fetch_raw_feed(feed_url: str):
    cfg = get_settings()
    for attempt in range(0, cfg.gtfs_realtime_retries):
        try:
            response = requests.get(feed_url, timeout=cfg.gtfs_timeout)
            response.raise_for_status()
            feed = pb.FeedMessage()
            feed.ParseFromString(response.content)
            return MessageToDict(
                feed, preserving_proto_field_name=True, use_integers_for_enums=True
            )
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
    return models.Feed.model_validate(feed_dict)
