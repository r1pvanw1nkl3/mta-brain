from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Table:
    headers: list[str]
    rows: list[list[str]]


@dataclass(frozen=True)
class Stack:
    items: list["View"]


@dataclass(frozen=True)
class Section:
    title: str
    subtitle: str | None = None
    body: Union["View", None] = None


View = Section | Table | Stack | str
