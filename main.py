import requests
import gtfs_realtime_pb2
import nyct_subway_pb2


def _fetch_data_feed(api_url: str) -> gtfs_realtime_pb2.FeedMessage:
    response = requests.get(api_url, timeout=10)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed


def main():
    _fetch_data_feed('https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace')
    

if __name__ == "__main__":
    main()

