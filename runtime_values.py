from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SExpression:
    name: str
    fields: tuple[Value, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or any(
            char.isspace() for char in self.name
        ):
            raise ValueError("S-expression constructor must be a nonempty token")
        object.__setattr__(self, "fields", tuple(self.fields))

    def __str__(self) -> str:
        return format_value(self)


Value = int | SExpression


def require_int(value: Value) -> int:
    if type(value) is not int:
        raise TypeError(f"Integer value expected, got {format_value(value)}")
    return value


def get_element(value: Value, index: Value) -> Value:
    index = require_int(index)
    if not isinstance(value, SExpression):
        raise TypeError(f"S-expression expected, got {format_value(value)}")
    if index < 0 or index >= len(value.fields):
        raise IndexError(f"Index {index} is out of bounds [0, {len(value.fields)})")
    return value.fields[index]


def _list_items(value: SExpression) -> list[Value] | None:
    items = []
    current = value
    while current.name == "cons" and len(current.fields) == 2:
        head, tail = current.fields
        items.append(head)
        if not isinstance(tail, SExpression):
            return None
        current = tail
    if current.name == "nil" and not current.fields:
        return items
    return None


def format_value(value: Value) -> str:
    if not isinstance(value, SExpression):
        return str(value)
    items = _list_items(value)
    if items is not None:
        return "{" + ", ".join(format_value(item) for item in items) + "}"
    if not value.fields:
        return value.name
    fields = ", ".join(format_value(field) for field in value.fields)
    return f"{value.name} ({fields})"
