from transit_core.core.engines.planner import PlannerEngine
from transit_core.core.repository import StopReader
from transit_core.messenger.address import NormalizationError, normalize_nyc_address
from transit_core.messenger.models import Message
from transit_core.messenger.parser import ParseError, parse_message
from transit_core.messenger.presenters import (
    present_arrivals_board,
    present_help,
    present_nearby_arrivals,
    present_nearby_stops,
    present_stop_search_results,
)

PLANNER_MAX_WALK_MINS = 5


class Handler:
    def __init__(self, stop_reader: StopReader, planner: PlannerEngine):
        self.stop_reader = stop_reader
        self.planner = planner

    async def handle(self, raw_text: str, sender_id: str) -> Message | None:
        parsed = parse_message(raw_text)
        if parsed is None:
            return None
        if isinstance(parsed, ParseError):
            return Message(receiver_id=sender_id, body=parsed.message)

        match parsed.command:
            case "arrivals":
                result = self.stop_reader.get_arrivals_board(
                    parsed.args["stop_id"], get_schedules=False
                )
                view = present_arrivals_board(result)
            case "search":
                result = self.stop_reader.fuzzy_station_search(
                    parsed.args["search_string"]
                )
                view = present_stop_search_results(result, parsed.args["search_string"])
            case "nearby":
                address_result = normalize_nyc_address(parsed.args["address"])
                if isinstance(address_result, NormalizationError):
                    return Message(receiver_id=sender_id, body=address_result.message)
                result = await self.stop_reader.get_stops_near_address(
                    address_result, 5
                )
                view = present_nearby_stops(result, parsed.args["address"])
            case "planner":
                address_result = normalize_nyc_address(parsed.args["address"])
                if isinstance(address_result, NormalizationError):
                    return Message(receiver_id=sender_id, body=address_result.message)
                result = await self.planner.get_arrivals_by_address(
                    address_result, PLANNER_MAX_WALK_MINS
                )
                view = present_nearby_arrivals(
                    result, parsed.args["address"], PLANNER_MAX_WALK_MINS
                )
            case "help":
                view = present_help()
            case _:
                raise AssertionError(
                    f"parser returned unexpected command: {parsed.command}"
                )

        return Message(receiver_id=sender_id, body=view)
