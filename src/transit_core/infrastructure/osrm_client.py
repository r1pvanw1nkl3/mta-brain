import logging
from typing import TYPE_CHECKING

import httpx

from transit_core.core.interfaces import StreetRoutingService
from transit_core.core.models import Coordinates

logger = logging.getLogger(__name__)


class OsrmClient:
    def __init__(self, osrm_url: str, http_client: httpx.AsyncClient):
        self.osrm_url = osrm_url.rstrip("/")
        self.http_client = http_client

    async def get_walk_times(
        self, user_location: Coordinates, stop_locations: dict[int, Coordinates]
    ) -> dict[int, float]:
        if not stop_locations:
            return {}

        stop_ids = list(stop_locations.keys())
        coords_list = [user_location] + [stop_locations[sid] for sid in stop_ids]

        path = ";".join([self._format_coordinates(c) for c in coords_list])

        try:
            response = await self.http_client.get(
                f"{self.osrm_url}/table/v1/foot/{path}",
                params={"sources": 0},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "Ok":
                raise RuntimeError(f"OSRM returned non-Ok code: {data.get('code')}")

            raw_walk_times = data["durations"][0][1:]
            return {
                stop_id: float(duration)
                for stop_id, duration in zip(stop_ids, raw_walk_times)
                if duration is not None
            }
        except httpx.HTTPStatusError as e:
            logger.exception(
                f"""OSRM returned an error status:
                {e.response.status_code} - {e.response.text}"""
            )
            raise
        except httpx.RequestError as e:
            logger.exception(f"Network error communicating with OSRM: {e}")
            raise
        except (KeyError, IndexError) as e:
            logger.exception(
                f"Malformed response from OSRM. Missing expected keys: {e}"
            )
            raise

    def _format_coordinates(self, coords: Coordinates) -> str:
        return f"{coords.lon},{coords.lat}"


if TYPE_CHECKING:
    _: StreetRoutingService = OsrmClient(
        osrm_url="...", http_client=httpx.AsyncClient()
    )
