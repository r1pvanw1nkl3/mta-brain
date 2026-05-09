from dataclasses import dataclass


@dataclass(frozen=True)
class Table:
    headers: list[str]
    rows: list[list[str]]


@dataclass(frozen=True)
class Section:
    title: str
    subtitle: str
    body: Table | str | None
