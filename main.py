"""CLI: каждый этап запускается отдельно.

  python main.py parse     [файлы]   разбор входа, без сети
  python main.py plan      [файлы]   что и какими чанками БУДЕТ отправлено, без сети
  python main.py translate [файлы]   перевод в кэш (--max-chunks N для пробного запуска)
  python main.py show      [файлы]   посмотреть кэш по этим файлам
  python main.py audio     [файлы]   озвучка в audio_cache/ (--limit N)
  python main.py build     [файлы]   сборка .apkg из кэша и аудио, без сети
  python main.py all       [файлы]   translate -> audio -> build

Папки:  input/ (.txt)   output/ (.apkg)   cache/ (translation_cache.json, audio/, pycache/)

translate / audio / build / all пропускают файлы, для которых в output/ уже есть .apkg
(--force: обработать заново). parse / plan / show работают со всеми файлами.
Без [файлы] берутся все *.txt из input/ (или --dir).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Служебный кэш Python (__pycache__) складываем в cache/pycache, а не рядом с кодом.
# Должно стоять ДО импорта остальных модулей проекта.
sys.pycache_prefix = str(Path(__file__).resolve().parent / "cache" / "pycache")

import argparse

from audio import AudioError, AudioStore
from cache import TranslationCache
from config import (AUDIO_DIR, CACHE_DIR, CACHE_PATH, INPUT_DIR, OUTPUT_DIR,
                    SENTENCE_PREVIEW_LENGTH)
from deck import MissingDataError, build_deck, collect_cards, write_package
from inputs import orphan_outputs, output_path, split_by_status
from parsing import Sentence, read_sentences
from transport import GoogleTransport, TransportError
from translation import Translator
from util import log, shorten


def cmd_parse(path, sentences, cache, args) -> int:
    for i, s in enumerate(sentences, 1):
        log(f"{i:3}. {s.text}\n     words: {', '.join(s.marked_words)}")
    log(f"Total: {len(sentences)} sentences, {sum(len(s.marked_words) for s in sentences)} words")
    return 0


def cmd_plan(path, sentences, cache, args) -> int:
    translator = Translator(None, cache)
    jobs, fallbacks = translator.plan(sentences)
    chunks = translator.chunks(jobs)
    log(f"To send: {len(jobs)} lines in {len(chunks)} chunks "
        f"(+ {len(fallbacks)} words without context)")
    for n, chunk in enumerate(chunks, 1):
        log(f"  chunk {n}: {len(chunk)} lines, {sum(len(j.line) + 1 for j in chunk)} chars")
        if args.show:
            for job in chunk:
                log(f"      [{job.kind}] {job.line}")
    return 0


def cmd_translate(path, sentences, cache, args) -> int:
    translator = Translator(GoogleTransport(), cache, max_chunks=args.max_chunks, log=log)
    try:
        translator.run(sentences)
    except TransportError as error:
        log(f"TRANSLATION ERROR: {error}\nProgress is saved in the cache; rerun to continue.")
        return 1
    if translator.fallback_words:
        log("No context for these words (check them): " + ", ".join(translator.fallback_words))
    done = sum(1 for s in sentences
               if (e := cache.get(s.text)) and e.is_complete(s.marked_words))
    log(f"Translated: {done}/{len(sentences)} sentences complete")
    return 0


def cmd_show(path, sentences, cache, args) -> int:
    for s in sentences:
        entry = cache.get(s.text)
        log(f"\nSRC: {s.text}")
        if entry is None or not entry.translation:
            log("  (no translation in cache)")
        else:
            log(f"RU : {entry.translation}")
        for word in s.marked_words:
            hint = entry.words.get(word) if entry else None
            if hint is None:
                log(f"  - {word}: (missing)")
            else:
                flag = "" if hint.in_context else "  [NO CONTEXT]"
                log(f"  - {word} -> {hint.hint}{flag}\n      raw: {hint.raw}")
    return 0


def cmd_audio(path, sentences, cache, args) -> int:
    store = AudioStore(AUDIO_DIR)
    texts = list(dict.fromkeys(s.text for s in sentences))
    generated = 0
    for i, text in enumerate(texts, 1):
        if args.limit is not None and generated >= args.limit:
            log("Limit reached, stopping.")
            break
        try:
            created = store.ensure(text)
        except AudioError as error:
            log(f"AUDIO ERROR: {error}")
            return 1
        generated += created
        log(f"[{i}/{len(texts)}] {'TTS ' if created else 'have'} {shorten(text, SENTENCE_PREVIEW_LENGTH)}")
    return 0


def cmd_build(path, sentences, cache, args) -> int:
    output = output_path(path, OUTPUT_DIR)
    store = AudioStore(AUDIO_DIR)
    try:
        cards = collect_cards(sentences, cache, store)
    except MissingDataError as error:
        log("Not enough data to build; run 'translate' / 'audio' first:")
        for problem in error.problems:
            log(f"  {problem}")
        return 1
    deck = build_deck(path.stem, cards)
    media = [store.path_for(t) for t in dict.fromkeys(s.text for s in sentences)]
    write_package(deck, media, output)
    log(f"Created: {output} ({len(cards)} cards)")
    return 0


def cmd_all(path, sentences, cache, args) -> int:
    for step in (cmd_translate, cmd_audio, cmd_build):
        code = step(path, sentences, cache, args)
        if code:
            return code
    return 0


COMMANDS = {
    "parse": cmd_parse, "plan": cmd_plan, "translate": cmd_translate, "show": cmd_show,
    "audio": cmd_audio, "build": cmd_build, "all": cmd_all,
}


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("files", nargs="*", help="входные .txt (по умолчанию все *.txt из input/)")
    common.add_argument("--dir", default=str(INPUT_DIR), help="папка с .txt (по умолчанию input/)")
    common.add_argument("--max-chunks", type=int, default=None, help="для translate/all: пробный запуск")
    common.add_argument("--limit", type=int, default=None, help="для audio/all: максимум озвучек за запуск")
    common.add_argument("--force", action="store_true", help="для build/all: перезаписать .apkg")
    common.add_argument("--show", action="store_true", help="для plan: печатать все строки чанков")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        sub.add_parser(name, parents=[common])
    return parser


SKIPS_BUILT = {"translate", "audio", "build", "all"}


def main() -> int:
    args = build_parser().parse_args()
    for directory in (INPUT_DIR, OUTPUT_DIR, CACHE_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    all_inputs = sorted(Path(args.dir).glob("*.txt"))
    files = [Path(f) for f in args.files] or all_inputs
    if not files:
        log(f"No .txt files in {args.dir}. Put your files there.")
        return 1

    if args.command in SKIPS_BUILT:
        files, built = split_by_status(files, OUTPUT_DIR, args.force)
        log(f"Files: {len(files) + len(built)} total, {len(built)} already built, "
            f"{len(files)} to process")
        for path in built:
            log(f"  skip: {path.name} (output/{output_path(path, OUTPUT_DIR).name} exists, use --force)")
        for path in orphan_outputs(all_inputs, OUTPUT_DIR):
            log(f"  note: output/{path.name} has no matching .txt in input/")

    cache = TranslationCache(CACHE_PATH)
    for path in files:
        sentences: list[Sentence] = read_sentences(path)
        if not sentences:
            log(f"SKIP: {path.name} (no [[marked]] words)")
            continue
        log(f"=== {path.name} ===")
        code = COMMANDS[args.command](path, sentences, cache, args)
        if code:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())