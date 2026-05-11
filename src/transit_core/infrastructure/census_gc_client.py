import logging
from typing import TYPE_CHECKING

import httpx

from transit_core.core.interfaces import GeocodingService
from transit_core.core.models import Coordinates, GeocodeMatch

logger = logging.getLogger(__name__)


class CensusGCClient:
    def __init__(self, geocoding_url: str, http_client: httpx.AsyncClient):
        self.geocoding_url = geocoding_url
        self.http_client = http_client

    async def get_coords(self, address: str) -> GeocodeMatch | None:
        try:
            response = await self.http_client.get(
                self.geocoding_url,
                params={
                    "address": address,
                    "benchmark": "Public_AR_Current",
                    "format": "json",
                },
            )
            response.raise_for_status()
            data = response.json()
            matches = data["result"]["addressMatches"]
            if not matches:
                return
            # we're just looking at the first match
            match = matches[0]
            matched_address = match["matchedAddress"]
            coords = Coordinates(
                lat=match["coordinates"]["y"],
                lon=match["coordinates"]["x"],
            )
            return GeocodeMatch(coords=coords, matched_address=matched_address)

        except httpx.HTTPStatusError as e:
            logger.exception(f"Census GC Service returned an error status: {e}")
            raise
        except httpx.RequestError as e:
            logger.exception(f"Network error communicating with Census GC Service: {e}")
            raise
        except (KeyError, IndexError) as e:
            logger.exception(
                f"Malformed response from Census GC Service. Missing expected keys: {e}"
            )
            raise


if TYPE_CHECKING:
    _: GeocodingService = CensusGCClient(
        geocoding_url="...", http_client=httpx.AsyncClient()
    )
