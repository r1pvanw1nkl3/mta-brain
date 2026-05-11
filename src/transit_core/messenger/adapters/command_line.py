import uuid

from transit_core.messenger.models import Message
from transit_core.messenger.views import Section, Stack, Table, View


class CommandLineAdapter:
    def __init__(self, handler):
        self.session_id = str(uuid.uuid4())
        self.handler = handler

    async def start(self):
        await self._message_loop()

    def format(self, view: View) -> str:
        if isinstance(view, str):
            return view
        if isinstance(view, Table):
            return self._format_table(view)
        if isinstance(view, Stack):
            return self._format_stack(view)
        return self._format_section(view)

    def _format_section(self, section: Section) -> str:
        parts = [section.title]
        if section.subtitle:
            parts.append(section.subtitle)
        if section.body is not None:
            parts.append("")
            parts.append(self.format(section.body))
        return "\n".join(parts)

    def _format_stack(self, stack: Stack) -> str:
        return "\n\n".join(self.format(item) for item in stack.items)

    def _format_table(self, table: Table) -> str:
        widths = [len(h) for h in table.headers]
        for row in table.rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))
        lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(table.headers))]
        for row in table.rows:
            lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(row)))
        return "\n".join(lines)

    async def send(self, message: Message):
        print(self.format(message.body))

    async def _message_loop(self):
        try:
            while True:
                command = input("> ")
                response = await self.handler.handle(command, self.session_id)
                if response is not None:
                    await self.send(response)
        except KeyboardInterrupt:
            return
