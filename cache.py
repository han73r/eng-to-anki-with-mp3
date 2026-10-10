"""Блок 5. JSON-кэш переводов: предложение -> перевод + подсказки к словам."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class WordHint:
    hint: str          # перевод слова
    raw: str           # что именно вернул Google для предложения с этим словом в кавычках
    in_context: bool   # False = слово переведено отдельно, подсказка может быть неточной


@dataclass
class SentenceEntry:
    source: str
    translation: str = ""
    words: dict[str, WordHint] = field(default_factory=dict)

    def is_complete(self, marked_words) -> bool:
        return bool(self.translation) and all(w in self.words for w in marked_words)


class TranslationCache:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: dict[str, SentenceEntry] = self._load()

    def get(self, source: str) -> SentenceEntry | None:
        return self._entries.get(source)

    def entry(self, source: str) -> SentenceEntry:
        """Вернуть запись, создав пустую, если её ещё нет."""
        if source not in self._entries:
            self._entries[source] = SentenceEntry(source)
        return self._entries[source]

    def save(self) -> None:
        data = {src: asdict(entry) for src, entry in self._entries.items()}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    def _load(self) -> dict[str, SentenceEntry]:
        if not self._path.exists():
            return {}
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return {
            src: SentenceEntry(
                source=value["source"],
                translation=value["translation"],
                words={w: WordHint(**h) for w, h in value["words"].items()},
            )
            for src, value in raw.items()
        }
