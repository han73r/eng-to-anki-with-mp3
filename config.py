"""Все настройки в одном месте."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"        # сюда кладём .txt
OUTPUT_DIR = BASE_DIR / "output"      # сюда падают готовые .apkg
CACHE_DIR = BASE_DIR / "cache"
CACHE_PATH = CACHE_DIR / "translation_cache.json"
AUDIO_DIR = CACHE_DIR / "audio"
PYCACHE_DIR = CACHE_DIR / "pycache"   # служебные файлы Python (см. main.py)

# --- Google (неофициальный endpoint, без ключа) ---
GOOGLE_URL = "https://translate.googleapis.com/translate_a/single"
# Идентификаторы клиента по приоритету. С сентября 2026 gtx отдаёт 429,
# при 429 транспорт пробует следующий.
GOOGLE_CLIENTS = ("dict-chrome-ex", "at", "gtx")
SOURCE_LANG = "en"
TARGET_LANG = "ru"
HTTP_TIMEOUT_SEC = 15
MAX_RETRIES = 3

# --- Чанки ---
GOOGLE_CHAR_LIMIT = 5000                              # лимит веб-переводчика
CHUNK_CHAR_LIMIT = int(GOOGLE_CHAR_LIMIT * 0.8)       # 4000 символов
CHUNK_MAX_LINES = 40                                  # потолок строк в чанке

# --- Паузы между запросами ---
REQUEST_DELAY_SEC = 1.5
AUDIO_DELAY_SEC = 1.0

# --- Anki ---
ANKI_MODEL_ID = 1607392319
STOP_WORDS = {"the", "a", "an", "to", "of", "over", "about", "around", "into", "out"}

# --- Валидация и лимиты ---
BAD_WORD_ROWS_PATH = BASE_DIR / "bad_word_rows.txt"
TARGET_SENTENCE_COUNT = 3
DEFAULT_MAX_ROWS = None

# --- Вывод ---
SENTENCE_PREVIEW_LENGTH = 80
MAX_HINT_LENGTH = 60