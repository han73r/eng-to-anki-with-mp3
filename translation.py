"""Блок 4. Оркестратор перевода: задания -> чанки -> транспорт -> кэш.

На каждое предложение:
  * строка с чистым предложением            -> перевод предложения;
  * по строке на каждое [[слово]], где в кавычки взято только оно
                                            -> подсказка (слово вырезается из кавычек в ответе).
Если кавычки потерялись, слово переводится отдельно (in_context=False).
Транспорт передаётся снаружи, поэтому в тестах подставляется фейковый.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable

from cache import TranslationCache, WordHint
from chunking import make_chunks
from config import CHUNK_CHAR_LIMIT, CHUNK_MAX_LINES, MAX_HINT_LENGTH, REQUEST_DELAY_SEC
from parsing import Sentence
from transport import Transport

SEPARATORS_PATTERN = re.compile(r"[-/()]")
QUOTED_PATTERN = re.compile(r"[«“\"„](.+?)[»”\"“]")


# ---------- чистые функции (тестируются без сети) ----------

def to_hint_query(word: str) -> str:
    return SEPARATORS_PATTERN.sub(" ", word).strip()


def quote_word(sentence_text: str, word: str) -> str | None:
    """Предложение, где в кавычки взято только `word`. None, если слова в тексте нет."""
    quoted, count = re.subn(
        rf"(?<!\w){re.escape(word)}(?!\w)",
        lambda m: f'"{m.group(0)}"',
        sentence_text,
        count=1,
    )
    return quoted if count else None


def looks_like_junk(hint: str) -> bool:
    hint = hint.strip()
    return (
        not hint
        or len(hint) > MAX_HINT_LENGTH
        or any(ch.isdigit() for ch in hint)
        or (len(hint) > 3 and hint.isupper())
    )


def match_case(hint: str, source_word: str, sentence_text: str) -> str:
    is_plain_word = source_word[:1].islower() or sentence_text.startswith(source_word)
    if is_plain_word and hint[:1].isupper():
        return hint[0].lower() + hint[1:]
    return hint


def extract_hint(translated_line: str, word: str, sentence_text: str) -> str | None:
    """Достать из переведённой строки то, что стоит в кавычках."""
    match = QUOTED_PATTERN.search(translated_line)
    if match and not looks_like_junk(match.group(1)):
        return match_case(match.group(1).strip(), word, sentence_text)
    return None


# ---------- оркестратор ----------

@dataclass(frozen=True)
class Job:
    kind: str            # "sentence" | "word" | "fallback"
    source: str          # исходное предложение (ключ кэша)
    word: str | None
    line: str            # что отправляем в Google
    raw: str = ""        # для fallback: что вернулось на попытку с кавычками


class Translator:
    def __init__(
        self,
        transport: Transport | None,
        cache: TranslationCache,
        max_chars: int = CHUNK_CHAR_LIMIT,
        max_lines: int = CHUNK_MAX_LINES,
        delay: float = REQUEST_DELAY_SEC,
        max_chunks: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
        log: Callable[[str], None] = print,
    ) -> None:
        self._transport = transport
        self._cache = cache
        self._max_chars, self._max_lines = max_chars, max_lines
        self._delay = delay
        self._max_chunks = max_chunks
        self._sleep = sleep
        self._log = log
        self._chunks_done = 0
        self._pending: list[Job] = []
        self.fallback_words: list[str] = []

    # --- планирование (без сети) ---

    def plan(self, sentences: list[Sentence]) -> tuple[list[Job], list[Job]]:
        """(основные задания, задания для слов, которые нельзя взять в кавычки)."""
        merged: dict[str, list[str]] = {}
        for s in sentences:
            words = merged.setdefault(s.text, [])
            words.extend(w for w in s.marked_words if w not in words)

        jobs: list[Job] = []
        fallbacks: list[Job] = []
        for text, words in merged.items():
            entry = self._cache.get(text)
            if entry is None or not entry.translation:
                jobs.append(Job("sentence", text, None, text))
            for word in words:
                if entry is not None and word in entry.words:
                    continue
                quoted = quote_word(text, word)
                if quoted:
                    jobs.append(Job("word", text, word, quoted))
                else:
                    fallbacks.append(Job("fallback", text, word, to_hint_query(word)))
        return jobs, fallbacks

    def chunks(self, jobs: list[Job]) -> list[list[Job]]:
        return make_chunks(jobs, self._max_chars, self._max_lines, key=lambda j: j.line)

    # --- выполнение ---

    def run(self, sentences: list[Sentence]) -> None:
        self._pending = []
        jobs, fallbacks = self.plan(sentences)
        if not jobs and not fallbacks:
            self._log("Nothing to translate: everything is in the cache.")
            return
        if self._process(jobs):
            self._process(fallbacks + self._pending)

    def _process(self, jobs: list[Job]) -> bool:
        """False, если остановились из-за max_chunks."""
        chunks = self.chunks(jobs)
        for number, chunk in enumerate(chunks, 1):
            if self._max_chunks is not None and self._chunks_done >= self._max_chunks:
                self._log("Chunk limit reached, stopping.")
                return False
            chars = sum(len(j.line) + 1 for j in chunk)
            self._log(f"Chunk {number}/{len(chunks)}: {len(chunk)} lines, {chars} chars")
            results = self._translate_lines([j.line for j in chunk])
            for job, result in zip(chunk, results):
                self._apply(job, result)
            self._cache.save()          # сохраняем после каждого чанка
            self._chunks_done += 1
        return True

    def _translate_lines(self, lines: list[str]) -> list[str]:
        """Отправить строки одним запросом. Если число строк в ответе не совпало,
        делим пополам и пробуем заново (вплоть до одной строки)."""
        response = self._transport.translate("\n".join(lines))  # type: ignore[union-attr]
        self._sleep(self._delay)
        parts = [p.strip() for p in re.split(r"\r?\n", response.strip())]
        if len(parts) == len(lines):
            return parts
        if len(lines) == 1:
            return [" ".join(parts)]
        self._log(f"  line count mismatch (sent {len(lines)}, got {len(parts)}), splitting")
        middle = len(lines) // 2
        return self._translate_lines(lines[:middle]) + self._translate_lines(lines[middle:])

    def _apply(self, job: Job, result: str) -> None:
        entry = self._cache.entry(job.source)
        if job.kind == "sentence":
            if result:
                entry.translation = result
            else:
                self._log(f"  empty translation for: {job.source}")
        elif job.kind == "word":
            hint = extract_hint(result, job.word, job.source)  # type: ignore[arg-type]
            if hint is None:
                self._pending.append(
                    Job("fallback", job.source, job.word, to_hint_query(job.word), raw=result)  # type: ignore[arg-type]
                )
            else:
                entry.words[job.word] = WordHint(hint, result, True)  # type: ignore[index]
        else:
            entry.words[job.word] = WordHint(result, job.raw, False)  # type: ignore[index]
            self.fallback_words.append(job.word)  # type: ignore[arg-type]
