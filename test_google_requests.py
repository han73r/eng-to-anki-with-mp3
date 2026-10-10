import requests
for client in ("gtx", "at", "dict-chrome-ex"):
    r = requests.get("https://translate.googleapis.com/translate_a/single",
        params={"client": client, "sl": "en", "tl": "ru", "dt": "t", "q": "hello"},
        headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    print(client, r.status_code)