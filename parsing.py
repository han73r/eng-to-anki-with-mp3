"""Блок 1. Разбор входного файла. Без сети."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from config import BAD_WORD_ROWS_PATH, TARGET_SENTENCE_COUNT
from util import log

MARKED_WORD_PATTERN = re.compile(r"\[\[(.*?)\]\]")
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")


def clean_markdown_bold(text: str) -> str:
    """Удаляет маркеры ** из текста (для озвучки и перевода)."""
    return BOLD_PATTERN.sub(r"\1", text)


def render_markdown_bold(text: str) -> str:
    """Заменяет маркеры **text** на <b>text</b> (для отображения в карточках Anki)."""
    return BOLD_PATTERN.sub(r"<b>\1</b>", text)


def normalize_tag(tag: str) -> str:
    """Приводит тег к lowercase snake_case (например: '[Daily Life & Survival]' -> 'daily_life_and_survival')."""
    cleaned = tag.strip().strip("[]").strip()
    cleaned = re.sub(r"\s*&\s*", " and ", cleaned)
    cleaned = re.sub(r"[^\w]+", "_", cleaned.lower()).strip("_")
    return re.sub(r"_+", "_", cleaned)


@dataclass(frozen=True)
class Sentence:
    text: str                       # предложение без разметки [[...]] и без **...** (для перевода и озвучки)
    marked_words: tuple[str, ...]   # слова из [[...]], без повторов, по порядку
    display_text: str = ""          # предложение с сохранённым <b>bold</b> (для карточек Anki)
    target: str = ""                # целевое слово/фраза (1-е поле)
    topic: str = ""                 # основная тема без скобок (2-е поле)
    tags: tuple[str, ...] = ()      # теги в lowercase snake_case, включая тег темы

    @classmethod
    def parse(cls, line: str) -> "Sentence":
        line = line.strip()
        if not line:
            return cls(text="", marked_words=(), display_text="")

        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            target = parts[0]
            middle_fields = parts[1:-1]
            sentence_part = parts[-1]
            raw_topic = next(
                (p for p in middle_fields if p.startswith("[") and p.endswith("]")),
                middle_fields[0] if middle_fields else "",
            )
            topic = normalize_tag(raw_topic)
            tags = tuple(normalize_tag(t) for t in middle_fields if normalize_tag(t))
        else:
            target = ""
            topic = ""
            tags = ()
            sentence_part = line

        clean_sentence = " ".join(sentence_part.split())
        words = (w.strip() for w in MARKED_WORD_PATTERN.findall(clean_sentence))
        marked_words = tuple(dict.fromkeys(w for w in words if w))
        unbracketed = MARKED_WORD_PATTERN.sub(r"\1", clean_sentence)
        text = clean_markdown_bold(unbracketed)
        display_text = render_markdown_bold(unbracketed)

        return cls(
            text=text,
            marked_words=marked_words,
            display_text=display_text,
            target=target,
            topic=topic,
            tags=tags,
        )


def parse_lines(lines: list[str]) -> list[Sentence]:
    return [Sentence.parse(line) for line in lines if line.strip()]


def validate_target_counts(
    sentences: list[Sentence],
    report_path: Path = BAD_WORD_ROWS_PATH,
    log_fn: Callable[[str], None] = log,
    source_name: str = "",
) -> list[str]:
    """Проверяет, что у каждой целевой фразы ровно TARGET_SENTENCE_COUNT строк.
    При несовпадении пишет в report_path и выводит предупреждение."""
    targets = [s.target for s in sentences if s.target]
    if not targets:
        return []
    counts = Counter(targets)
    bad_targets = [t for t, c in counts.items() if c != TARGET_SENTENCE_COUNT]
    if bad_targets:
        prefix = f"[{source_name}] " if source_name else ""
        lines = [
            f"{prefix}Target '{t}': {counts[t]} rows (expected {TARGET_SENTENCE_COUNT})"
            for t in bad_targets
        ]
        with report_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        log_fn(f"[WARNING] {len(bad_targets)} target phrases have != {TARGET_SENTENCE_COUNT} rows. Saved to {report_path.name}:")
        for msg in lines[:10]:
            log_fn(f"  - {msg}")
        if len(lines) > 10:
            log_fn(f"  ... and {len(lines) - 10} more")
    return bad_targets


def read_sentences(
    path: Path,
    max_rows: int | None = None,
    report_path: Path = BAD_WORD_ROWS_PATH,
    validate: bool = True,
) -> list[Sentence]:
    """Только предложения, в которых есть хотя бы одно [[слово]]."""
    sentences = parse_lines(path.read_text(encoding="utf-8").splitlines())
    filtered = [s for s in sentences if s.marked_words]
    if max_rows is not None:
        filtered = filtered[:max_rows]
    if validate:
        validate_target_counts(filtered, report_path=report_path, source_name=path.name)
    return filtered

