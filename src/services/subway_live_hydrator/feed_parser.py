import logging
import time

import requests
from google.protobuf.json_format import MessageToDict, MessageToJson
from google.protobuf.message import DecodeError

import transit_core.core.models as models
import transit_core.core.protos.gtfs_realtime_pb2 as pb
from transit_core.config import get_settings

logger = logging.getLogger(__name__)


def fetch_live_feed(feed_url: str) -> models.Feed:
    settings = get_settings()
    for attempt in range(0, settings.gtfs_realtime_retries):
        try:
            response = requests.get(feed_url, timeout=settings.gtfs_timeout)
            response.raise_for_status()
            feed = pb.FeedMessage()
            feed.ParseFromString(response.content)

            print(
                MessageToJson(
                    feed, preserving_proto_field_name=True, use_integers_for_enums=True
                )
            )

            feed_dict = MessageToDict(
                feed, preserving_proto_field_name=True, use_integers_for_enums=True
            )
            return models.Feed.model_validate(feed_dict)
        except (requests.RequestException, DecodeError, requests.HTTPError) as e:
            error_type = type(e).__name__
            print(f"Error on attempt {attempt + 1}: {error_type}")
            if attempt < settings.gtfs_realtime_retries:
                time.sleep(settings.gtfs_retry_delay)
            else:
                raise e
