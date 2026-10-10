# Anki Deck Builder (English → Russian, with audio)

Turn plain text files with example sentences into ready-to-import **Anki decks (`.apkg`)**.

You write English sentences and mark the words you want to learn with `[[double brackets]]`.
The tool then:

1. **translates** every sentence and every marked word *in context* (free, no API key),
2. **generates speech** for every sentence (gTTS),
3. **builds an Anki package** with one card per marked word.

Everything is cached on disk, so re-runs are fast and never repeat work that has already been done.

---

## Table of contents

- [Quick start](#quick-start)
- [Input format](#input-format)
- [What the cards look like](#what-the-cards-look-like)
- [Folder layout](#folder-layout)
- [Commands](#commands)
- [How it works](#how-it-works)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Tests](#tests)
- [Project structure](#project-structure)
- [Limitations](#limitations)

---

## Quick start

**Requirements:** Python 3.9 or newer and an internet connection (for translation and speech).

```bash
pip install genanki gtts requests
```

1. Put your `.txt` files into the `input/` folder (it is created on the first run).
2. Run:

   ```bash
   python main.py all
   ```

3. Find your decks in `output/` and open them with Anki (double-click the `.apkg`, or *File → Import*).

> **Tip:** do a small trial run first, see [Recommended workflow](#recommended-workflow).

---

## Input format

One sentence per line. Wrap each word or phrase you want to learn in `[[...]]`:

```text
She decided to [[look into]] the matter.
I [[like]] green [[tea]].
Lines without any marked word are ignored.
```

- Phrases with several words are fine: `[[look into]]`.
- A sentence with several marked words produces several cards (one per word).
- Blank lines are ignored.
- Files must be UTF-8 encoded.

The file name becomes the deck name: `input/words 01.txt` → `output/words 01.apkg`.

---

## What the cards look like

For the sentence `She decided to [[look into]] the matter.`:

| Side | Content |
|------|---------|
| **Front** | `She decided to .. in.. the matter.`<br>`(изучить)` — the sentence with the word partially masked, plus a Russian hint for the word *in this context* |
| **Back** | Russian translation of the whole sentence, then the original sentence with the word in **bold**, then an audio player for the sentence |

Short words and stop words (`the`, `to`, `of`, ...) are fully masked as `..`; longer words keep their first one or two letters.

---

## Folder layout

```text
anki_builder/
├── *.py                      # the program
├── input/                    # your .txt files go here
├── output/                   # finished .apkg files appear here
└── cache/
    ├── translation_cache.json   # translations (human-readable, safe to inspect)
    ├── audio/                   # generated .mp3 files, named by sentence hash
    └── pycache/                 # Python's compiled bytecode (safe to delete)
```

All folders are created automatically on the first run.

### Already-built files are skipped

For `translate`, `audio`, `build` and `all`, a `.txt` file is **skipped** when `output/<same name>.apkg` already exists:

```text
Files: 10 total, 3 already built, 7 to process
  skip: two.txt (output/two.apkg exists, use --force)
  note: output/deleted.apkg has no matching .txt in input/
```

- Matching is done by file name (`input/two.txt` ↔ `output/two.apkg`).
- Use `--force` to rebuild everything (for example after editing a `.txt`).
- The `note:` line points to `.apkg` files whose `.txt` no longer exists.
- `parse`, `plan` and `show` are inspection commands and never skip anything.

---

## Commands

Every stage can be run **separately**, so you can check the result before moving on.

```text
python main.py <command> [files...] [options]
```

| Command | What it does | Uses network |
|---------|--------------|:---:|
| `parse` | Shows how the input was parsed (sentences and marked words) | no |
| `plan` | Shows what *would* be sent to Google and in how many chunks | no |
| `translate` | Translates and writes results to the translation cache | yes |
| `show` | Prints the cache for these files: translation, hints, raw Google answers | no |
| `audio` | Generates missing `.mp3` files into `cache/audio/` | yes |
| `build` | Builds `.apkg` from the cache and audio files | no |
| `all` | `translate` → `audio` → `build` | yes |

| Option | Applies to | Meaning |
|--------|-----------|---------|
| `files...` | all | Process only these `.txt` files (default: every `*.txt` in `input/`) |
| `--dir PATH` | all | Read `.txt` files from another folder |
| `--max-chunks N` | `translate`, `all` | Send at most N chunks (trial run) |
| `--limit N` | `audio`, `all` | Generate at most N audio files per run |
| `--force` | `translate`, `audio`, `build`, `all` | Do not skip files that already have an `.apkg` |
| `--show` | `plan` | Print every line of every chunk |

### Recommended workflow

```bash
python main.py parse                    # 1. is the input read correctly?
python main.py plan --show              # 2. what will be sent?
python main.py translate --max-chunks 1 # 3. send just one chunk
python main.py show                     # 4. check translations and word hints
python main.py translate                # 5. translate the rest
python main.py audio --limit 5          # 6. try a few audio files
python main.py all                      # 7. finish everything
```

---

## How it works

### Translation in context

A marked word is ambiguous on its own (`like` can be a verb or a preposition), so each word is translated **inside its sentence**. For every sentence the tool prepares:

- one line with the **plain sentence** → its Russian translation;
- one line **per marked word**, where *only that word* is wrapped in quotes:

  ```text
  She decided to "look into" the matter.
  ```

Translators usually keep the quotes around the corresponding word of the translation, so the hint is cut out from between them. If the quotes are lost, the word is translated alone and flagged as `in_context: false` (`[NO CONTEXT]` in `show`), because such a hint may be inaccurate.

### Chunking

To avoid hundreds of tiny requests (and being rate limited), lines are grouped into **chunks** and each chunk is sent as a single request, one line per `\n`:

- at most **4000 characters** (80 % of Google's ~5000 limit) and **40 lines** per chunk;
- after each answer the number of lines is verified; if Google merged or dropped lines, the chunk is **split in half and retried**, down to a single line;
- the cache is saved **after every chunk**, so an interrupted run loses nothing.

### Translation cache

`cache/translation_cache.json` stores one record per sentence, with the raw Google answer so you can see exactly how each hint was obtained:

```json
{
  "She decided to look into the matter.": {
    "source": "She decided to look into the matter.",
    "translation": "Она решила изучить этот вопрос.",
    "words": {
      "look into": {
        "hint": "изучить",
        "raw": "Она решила \"изучить\" этот вопрос.",
        "in_context": true
      }
    }
  }
}
```

Only missing pieces are requested on later runs. For example, adding a new `[[word]]` to an already translated sentence sends just one extra line.

### Audio

Speech is generated per sentence with [gTTS](https://pypi.org/project/gTTS/) and stored as `cache/audio/<sha1-of-sentence>.mp3`. Existing files are never regenerated. Audio is not chunked: one sentence is one request.

---

## Configuration

All settings live in `config.py`:

| Setting | Default | Meaning |
|---------|---------|---------|
| `INPUT_DIR`, `OUTPUT_DIR`, `CACHE_DIR` | `input/`, `output/`, `cache/` | Folder locations |
| `GOOGLE_CLIENTS` | `("dict-chrome-ex", "at", "gtx")` | Client identifiers to try, in order |
| `CHUNK_CHAR_LIMIT` | `4000` | Max characters per chunk |
| `CHUNK_MAX_LINES` | `40` | Max lines per chunk |
| `REQUEST_DELAY_SEC` | `1.5` | Pause after each translation request |
| `AUDIO_DELAY_SEC` | `1.0` | Pause after each audio request |
| `SOURCE_LANG`, `TARGET_LANG` | `en`, `ru` | Translation languages |
| `STOP_WORDS` | `the, a, an, ...` | Words that are fully masked on the card front |

---

## Troubleshooting

### `HTTP 429` / "Google translate: HTTP 429 for all clients"

The tool uses Google's **unofficial, keyless** translation endpoint. Google changes or restricts it from time to time. Since around **September 2026** the former default client identifier `gtx` returns `429` for many users, which is why `dict-chrome-ex` is tried first and `at` / `gtx` are kept as fallbacks.

What to do:

1. Run `python main.py translate --max-chunks 1` again later: temporary blocks usually clear within an hour or two.
2. Check which identifier works for you:

   ```python
   import requests
   for client in ("gtx", "at", "dict-chrome-ex"):
       r = requests.get("https://translate.googleapis.com/translate_a/single",
           params={"client": client, "sl": "en", "tl": "ru", "dt": "t", "q": "hello"},
           headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
       print(client, r.status_code)
   ```

3. Put a working identifier first in `GOOGLE_CLIENTS`, and/or raise `REQUEST_DELAY_SEC`.

Progress is always saved in the cache, so you can simply re-run the command to continue.

### `ImportError: cannot import name ... from 'config'`

Some project files are from different versions. Make sure **all** `.py` files in the folder come from the same download.

### Some hints are marked `[NO CONTEXT]`

The translator dropped the quotes around that word, so it was translated on its own. Check these hints manually with `python main.py show`.

### `Not enough data to build`

`build` does not use the network. Run `translate` and `audio` first (or just `all`); the message lists the sentences that are still missing.

### What is `__pycache__`?

Python stores compiled bytecode there to start faster. It is harmless and can be deleted at any time. This project keeps it under `cache/pycache/`.

---

## Tests

The tests run **without network access** (Google and gTTS are replaced with fakes), so they never hit any API:

```bash
python -m unittest -v
```

They cover parsing, chunking, the Google transport (fallback between clients), the translation orchestrator (cache reuse, split on line mismatch, lost quotes), the caches, audio, card building and the `.txt` ↔ `.apkg` matching.

---

## Project structure

Each block has a single responsibility and can be tested in isolation.

| File | Responsibility | Network |
|------|----------------|:---:|
| `main.py` | Command-line interface, wires the blocks together | – |
| `config.py` | All settings and paths | – |
| `parsing.py` | `.txt` → sentences with marked words | no |
| `chunking.py` | Splits lines into chunks by size and count | no |
| `transport.py` | The only code that talks to Google Translate | yes |
| `translation.py` | Builds jobs, sends chunks, verifies answers, extracts hints | via transport |
| `cache.py` | JSON translation cache | no |
| `audio.py` | gTTS with an on-disk audio cache | yes |
| `deck.py` | Card text and `.apkg` building (genanki) | no |
| `inputs.py` | Matching of `input/*.txt` and `output/*.apkg` | no |
| `util.py` | Logging and small helpers | no |
| `test_*.py` | Offline unit tests | no |

The translator receives its transport as a constructor argument, so tests simply pass in a fake object instead of the real Google client.

---

## Limitations

- **Unofficial services.** Both translation and speech use free, keyless Google endpoints that can change or be rate limited without notice. There is no SLA.
- **English → Russian** is what the defaults and the masking rules are designed for. Changing `SOURCE_LANG` / `TARGET_LANG` is possible, but the stop-word list and the gTTS language (`lang="en"` in `audio.py`) are English-specific.
- **Machine translation** can be wrong. Use `python main.py show` to review the hints before importing the deck.
- The "already built" check only looks at whether the `.apkg` exists. If you edit a `.txt` that was already built, run with `--force`.
