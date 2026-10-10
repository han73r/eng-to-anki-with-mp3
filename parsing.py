"""Блок 1. Разбор входного файла. Без сети."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MARKED_WORD_PATTERN = re.compile(r"\[\[(.*?)\]\]")


@dataclass(frozen=True)
class Sentence:
    text: str                       # предложение без разметки
    marked_words: tuple[str, ...]   # слова из [[...]], без повторов, по порядку

    @classmethod
    def parse(cls, line: str) -> "Sentence":
        line = " ".join(line.split())
        words = (w.strip() for w in MARKED_WORD_PATTERN.findall(line))
        return cls(
            text=MARKED_WORD_PATTERN.sub(r"\1", line),
            marked_words=tuple(dict.fromkeys(w for w in words if w)),
        )


def parse_lines(lines: list[str]) -> list[Sentence]:
    return [Sentence.parse(line) for line in lines if line.strip()]


def read_sentences(path: Path) -> list[Sentence]:
    """Только предложения, в которых есть хотя бы одно [[слово]]."""
    sentences = parse_lines(path.read_text(encoding="utf-8").splitlines())
    return [s for s in sentences if s.marked_words]
