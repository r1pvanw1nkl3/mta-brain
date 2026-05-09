import uuid
from typing import Any

from transit_core.messenger.models import Message


class command_line:
    def __init__(self, handler):
        self.id = uuid.uuid4()
        self.handler = handler

    def start(self):
        return

    def format(self, message: Any):
        return message

    def send(self, message: Message):
        print(message.message_txt)

    def message_loop(self):
        try:
            while True:
                command = input("> ")
                response = self.handler.handle(command)
                if response:
                    self.send(response.message)
        except KeyboardInterrupt:
            return
