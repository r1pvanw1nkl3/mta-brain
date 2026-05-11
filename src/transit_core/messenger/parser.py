from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedCommand:
    command: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ParseError:
    message: str


def parse_message(message: str) -> ParsedCommand | ParseError | None:
    if not message or message[0] != "!":
        return None

    commands = message[1:].split(" ")

    match commands[0]:
        case "arrivals":
            if len(commands) > 1:
                return ParsedCommand("arrivals", {"stop_id": commands[1]})
            return ParseError("usage: !arrivals <stop_id>")
        case _:
            return ParseError(f"unknown command: {commands[0]}")
