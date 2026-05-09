from transit_core.core.engines.planner import PlannerEngine
from transit_core.core.repository import StopReader, TripReader


class Parser:
    def __init__(
        self,
        trip_reader: TripReader,
        stop_reader: StopReader,
        planner_engine: PlannerEngine,
    ):
        self.trip_reader = trip_reader
        self.stop_reader = stop_reader
        self.planner_engine = planner_engine

    def parse_message(self, message: str):
        if message[0] != "!":
            return

        commands = message[1:].split(" ")

        match commands[0]:
            case "arrivals":
                result = self.stop_reader.get_arrivals_board(
                    stop_id=commands[1], get_schedules=False
                )
            case _:
                print("Command not found")

        return result
