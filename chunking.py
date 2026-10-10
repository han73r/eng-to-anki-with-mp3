"""Блок 2. Нарезка на чанки. Чистая функция, без сети."""
from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def make_chunks(
    items: list[T],
    max_chars: int,
    max_lines: int,
    key: Callable[[T], str] = lambda item: item,  # type: ignore[assignment,return-value]
) -> list[list[T]]:
    """Жадно собирает элементы в чанки: не больше max_chars символов
    (с учётом переводов строк) и не больше max_lines элементов.
    Слишком длинный элемент попадает в отдельный чанк."""
    chunks: list[list[T]] = []
    current: list[T] = []
    size = 0
    for item in items:
        cost = len(key(item)) + 1
        if current and (size + cost > max_chars or len(current) >= max_lines):
            chunks.append(current)
            current, size = [], 0
        current.append(item)
        size += cost
    if current:
        chunks.append(current)
    return chunks
