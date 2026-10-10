"""Проверка: отвечает ли бесплатный Google-переводчик и не режет ли он запросы.

Запуск:  python google_check.py
Зависимость: pip install requests
"""

import time

import requests

URL = "https://translate.googleapis.com/translate_a/single"
DELAY_SEC = 1.0  # пауза между запросами; поменяйте, если Google начнёт отдавать 429

# Последние два примера проверяют кавычки вокруг слова, как это делает основной скрипт.
TESTS = [
    "I love learning languages.",
    "She decided to look into the matter.",
    'She decided to "look into" the matter.',
    'He tried to "figure" it out.',
]


def translate(text: str) -> str:
    response = requests.post(
        URL,
        params={"client": "gtx", "sl": "en", "tl": "ru", "dt": "t"},
        data={"q": text},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    print(f"  HTTP {response.status_code}")
    response.raise_for_status()
    return "".join(chunk[0] for chunk in response.json()[0] if chunk and chunk[0])


def main() -> None:
    ok = 0
    for number, text in enumerate(TESTS, 1):
        print(f"[{number}/{len(TESTS)}] {text}")
        started = time.time()
        try:
            result = translate(text)
            print(f"  -> {result}  ({time.time() - started:.2f} c)")
            ok += 1
        except Exception as error:
            print(f"  ОШИБКА: {error}")
            if "429" in str(error):
                print("  Google ограничил запросы. Увеличьте DELAY_SEC или подождите.")
                break
        time.sleep(DELAY_SEC)

    print(f"\nУспешно: {ok} из {len(TESTS)}")


if __name__ == "__main__":
    main()