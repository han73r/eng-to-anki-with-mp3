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
    sentence: str                  # отображаемое предложение (с сохранением <b>)
    plain_sentence: str            # чистый текст предложения (без разметки)
    word: str
    hint: str
    translation: str
    audio_name: str
    topic: str = ""
    tags: tuple[str, ...] = ()


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
                    sentence=s.display_text or s.text,
                    plain_sentence=s.text,
                    word=word,
                    hint=entry.words[word].hint,
                    translation=entry.translation,
                    audio_name=audio.name_for(s.text),
                    topic=s.topic,
                    tags=s.tags,
                ))
    if problems:
        raise MissingDataError(problems)
    return cards


def build_decks(base_name: str, cards: list[CardData]) -> list[genanki.Deck]:
    """Создаёт подколоды по темам (Option A: base_name::topic) и назначает теги карточкам."""
    by_topic: dict[str, list[CardData]] = {}
    for c in cards:
        by_topic.setdefault(c.topic, []).append(c)

    decks: list[genanki.Deck] = []
    for topic, topic_cards in by_topic.items():
        deck_name = f"{base_name}::{topic}" if topic else base_name
        deck_id = zlib.crc32(deck_name.encode("utf-8"))
        deck = genanki.Deck(deck_id, deck_name)
        for c in topic_cards:
            front = build_front(c.sentence, c.word, c.hint)
            back = build_back(c.sentence, c.word, c.translation, c.audio_name)
            note = genanki.Note(model=ANKI_MODEL, fields=[front, back], tags=list(c.tags))
            deck.add_note(note)
        decks.append(deck)
    return decks


def build_deck(name: str, cards: list[CardData]) -> genanki.Deck:
    """Для обратной совместимости: собирает все карточки в одну колоду."""
    deck = genanki.Deck(zlib.crc32(name.encode("utf-8")), name)
    for c in cards:
        front = build_front(c.sentence, c.word, c.hint)
        back = build_back(c.sentence, c.word, c.translation, c.audio_name)
        deck.add_note(genanki.Note(model=ANKI_MODEL, fields=[front, back], tags=list(c.tags)))
    return deck


def write_package(deck_or_decks: genanki.Deck | list[genanki.Deck], media_paths: list[Path], output: Path) -> None:
    package = genanki.Package(deck_or_decks)
    package.media_files = [str(p) for p in media_paths]
    package.write_to_file(str(output))
