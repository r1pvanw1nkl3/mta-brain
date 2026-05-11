from transit_core.core.repository import StopReader
from transit_core.messenger.models import Message
from transit_core.messenger.parser import ParseError, parse_message
from transit_core.messenger.presenters import present_arrivals_board


class Handler:
    def __init__(self, stop_reader: StopReader):
        self.stop_reader = stop_reader

    def handle(self, raw_text: str, sender_id: str) -> Message | None:
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
            case _:
                raise AssertionError(
                    f"parser emitted unknown command: {parsed.command}"
                )

        return Message(receiver_id=sender_id, body=view)
