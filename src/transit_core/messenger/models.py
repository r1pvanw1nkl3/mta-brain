from dataclasses import dataclass

from transit_core.messenger.views import View


@dataclass(frozen=True)
class Message:
    receiver_id: str
    body: View
