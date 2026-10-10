"""Блок 7. Сборка Anki. Без сети: берёт готовое из кэша и аудио."""
from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from pathlib import Path

import genanki

from audio import AudioStore
from cache import TranslationCache
from config import ANKI_MODEL_ID, SENTENCE_PREVIEW_LENGTH, STOP_WORDS
from parsing import Sentence
from util import shorten

ANKI_MODEL = genanki.Model(
    ANKI_MODEL_ID,
    "Basic",
    fields=[{"name": "Front"}, {"name": "Back"}],
    templates=[{"name": "Card 1", "qfmt": "{{Front}}", "afmt": "{{FrontSide}}<hr>{{Back}}"}],
)


class MissingDataError(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class CardData:
    sentence: str
    word: str
    hint: str
    translation: str
    audio_name: str


def mask_word(word: str) -> str:
    word = word.strip()
    if word.lower() in STOP_WORDS or len(word) < 3:
        return ".."
    if len(word) <= 4:
        return word[0] + ".."
    return word[:2] + ".."


def build_front(sentence_text: str, word: str, hint: str) -> str:
    masked = sentence_text
    for part in word.split():
        masked = re.sub(rf"\b{re.escape(part)}\b", mask_word(part), masked)
    return f"{masked}<br>({hint})"


def build_back(sentence_text: str, word: str, translation: str, audio_name: str) -> str:
    highlighted = re.sub(
        rf"\b{re.escape(word)}\b",
        lambda m: f"<b>{m.group(0)}</b>",
        sentence_text,
        count=1,
    )
    return f"{translation}<br><hr>{highlighted}<br>[sound:{audio_name}]"


def collect_cards(
    sentences: list[Sentence], cache: TranslationCache, audio: AudioStore
) -> list[CardData]:
    cards: list[CardData] = []
    problems: list[str] = []
    for s in sentences:
        preview = shorten(s.text, SENTENCE_PREVIEW_LENGTH)
        entry = cache.get(s.text)
        if entry is None or not entry.is_complete(s.marked_words):
            problems.append(f"no translation: {preview}")
        elif not audio.has(s.text):
            problems.append(f"no audio: {preview}")
        else:
            for word in s.marked_words:
                cards.append(CardData(
                    s.text, word, entry.words[word].hint, entry.translation, audio.name_for(s.text)
                ))
    if problems:
        raise MissingDataError(problems)
    return cards


def build_deck(name: str, cards: list[CardData]) -> genanki.Deck:
    deck = genanki.Deck(zlib.crc32(name.encode("utf-8")), name)
    for c in cards:
        front = build_front(c.sentence, c.word, c.hint)
        back = build_back(c.sentence, c.word, c.translation, c.audio_name)
        deck.add_note(genanki.Note(model=ANKI_MODEL, fields=[front, back]))
    return deck


def write_package(deck: genanki.Deck, media_paths: list[Path], output: Path) -> None:
    package = genanki.Package(deck)
    package.media_files = [str(p) for p in media_paths]
    package.write_to_file(str(output))
