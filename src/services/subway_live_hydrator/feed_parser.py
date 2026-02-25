import logging
import time

import requests
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from pydantic import ValidationError

import transit_core.core.models as models
from transit_core.config import get_settings
from transit_core.core.exceptions import FeedFetchError, FeedParseError
from transit_core.core.protos import nyct_subway_pb2
from transit_core.core.protos.gtfs_realtime_pb2 import FeedMessage  # type: ignore

logger = logging.getLogger(__name__)


def fetch_raw_feed(feed_url: str):
    cfg = get_settings()
    for attempt in range(0, cfg.gtfs_realtime_retries):
        try:
            logger.info(
                "Attempting to fetch feed",
                extra={"feed_url": feed_url, "attempt": attempt + 1},
            )
            response = requests.get(feed_url, timeout=cfg.gtfs_timeout)
            response.raise_for_status()
            logger.info(
                "Fetched feed",
                extra={
                    "feed_url": feed_url,
                    "status_code": response.status_code,
                    "size_bytes": len(response.content),
                },
            )
            feed = FeedMessage()
            feed.ParseFromString(response.content)
            feed_dict = MessageToDict(
                feed,
                preserving_proto_field_name=True,
                use_integers_for_enums=True,
                descriptor_pool=nyct_subway_pb2.DESCRIPTOR.pool,
            )
            entity_count = len(feed_dict.get("entity", []))
            logger.info(
                "Parsed feed",
                extra={"feed_url": feed_url, "entity_count": entity_count},
            )
            return feed_dict
        except (requests.RequestException, DecodeError) as e:
            error_type = type(e).__name__
            logger.warning(
                "Error fetching feed, retrying",
                extra={
                    "feed_url": feed_url,
                    "attempt": attempt + 1,
                    "error_type": error_type,
                    "error": str(e),
                },
            )
            if attempt < cfg.gtfs_realtime_retries - 1:
                time.sleep(cfg.gtfs_retry_delay)
            else:
                logger.exception(
                    "Terminal failure fetching feed", extra={"feed_url": feed_url}
                )
                raise FeedFetchError(
                    f"""Failed to fetch feed {feed_url} after
                    {cfg.gtfs_realtime_retries} attempts"""
                ) from e
    return None


def validate_feed(feed_dict):
    logger.debug("Validating feed")
    try:
        return models.Feed.model_validate(feed_dict)
    except ValidationError as e:
        logger.exception("Feed validation failed")
        raise FeedParseError(f"Feed validation failed: {e}") from e
