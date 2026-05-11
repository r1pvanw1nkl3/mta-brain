from typing import Any, ContextManager, Protocol, runtime_checkable

from transit_core.core.models import (
    Coordinates,
    GeocodeMatch,
    NearbyStop,
    StopSearchResult,
)


@runtime_checkable
class StreetRoutingService(Protocol):
    async def get_walk_times(
        self, user_location: Coordinates, stop_locations: dict[int, Coordinates]
    ) -> dict[int, float]: ...


@runtime_checkable
class StateStore(Protocol):
    def batch_session(self) -> ContextManager: ...
    def set_kv(self, key: str, value: str, expiry) -> None: ...
    def get_kv(self, key: str) -> str | None: ...
    def get_zset(self, key: str, max_score: float = float("inf")) -> dict[str, int]: ...
    def sync_set(
        self, key: str, mapping: dict[str, int], min_score: int, expiry
    ) -> None: ...
    def check_and_update_timestamp(self, key: str, timestamp: int) -> bool: ...


@runtime_checkable
class StaticStore(Protocol):
    def get_nearby_stops(self, coords: Coordinates, count: int) -> list[NearbyStop]: ...

    def get_scheduled_arrivals(
        self, stop_id: str, lookahead_minutes: int = 60
    ) -> list[dict[str, Any]]: ...

    def get_trip_metadata(self, trip_id: str) -> dict[str, Any] | None: ...

    def get_stop_name(self, stop_id: str) -> str: ...

    def get_trip_stop_times(self, trip_id: str) -> dict[str, int]: ...

    def get_stop_names(self, stop_ids: list[str]) -> dict[str, str]: ...

    def fuzzy_station_search(
        self,
        search_query: str,
        ilike_query: str,
        has_single_char: bool,
        regex_pattern: str | None = None,
    ) -> list[StopSearchResult]: ...


@runtime_checkable
class GeocodingService(Protocol):
    async def get_coords(self, address: str) -> GeocodeMatch | None: ...
