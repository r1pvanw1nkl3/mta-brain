from typing import Any, Protocol, runtime_checkable

from transit_core.messenger.models import Message


@runtime_checkable
class MessengerService(Protocol):
    def start(): ...
    def format(message: Any) -> Any: ...
    def send(message: Message): ...
