from typing import Protocol, runtime_checkable

from transit_core.messenger.models import Message


@runtime_checkable
class MessengerService(Protocol):
    async def start(self): ...
    async def send(self, message: Message): ...
