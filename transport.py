"""Блок 3. Единственное место, которое ходит в Google за переводом."""
from __future__ import annotations

import time
from typing import Callable, Protocol

import requests

from config import (GOOGLE_CLIENTS, GOOGLE_URL, HTTP_TIMEOUT_SEC, MAX_RETRIES,
                    SOURCE_LANG, TARGET_LANG)


class TransportError(Exception):
    """Не удалось получить перевод (лимит, сеть, неожиданный ответ)."""


class Transport(Protocol):
    def translate(self, text: str) -> str: ...


class GoogleTransport:
    def __init__(
        self,
        source: str = SOURCE_LANG,
        target: str = TARGET_LANG,
        clients: tuple[str, ...] = GOOGLE_CLIENTS,
        retries: int = MAX_RETRIES,
        sleep: Callable[[float], None] = time.sleep,
        session: requests.Session | None = None,
    ) -> None:
        self._source, self._target = source, target
        self._clients = list(clients)
        self._retries = retries
        self._sleep = sleep
        self._session = session or requests.Session()
        self._session.headers["User-Agent"] = "Mozilla/5.0"

    def translate(self, text: str) -> str:
        """429 = клиент заблокирован: сразу пробуем следующий идентификатор (без пауз).
        Сетевые ошибки и 5xx повторяем с паузой."""
        blocked: list[str] = []
        for client in self._clients:
            outcome = self._try_client(client, text)
            if outcome is not None:
                # запоминаем рабочий клиент: следующие запросы начнутся с него
                self._clients.remove(client)
                self._clients.insert(0, client)
                return outcome
            blocked.append(client)
        raise TransportError(
            "Google translate: HTTP 429 for all clients "
            f"({', '.join(blocked)}). Подождите или смените способ перевода."
        )

    def _try_client(self, client: str, text: str) -> str | None:
        """Перевод, либо None если клиент получил 429."""
        last_error = "unknown error"
        for attempt in range(self._retries):
            try:
                response = self._session.post(
                    GOOGLE_URL,
                    params={"client": client, "sl": self._source, "tl": self._target, "dt": "t"},
                    data={"q": text},
                    timeout=HTTP_TIMEOUT_SEC,
                )
            except requests.RequestException as error:
                last_error = str(error)
            else:
                if response.status_code == 200:
                    return self._parse(response)
                if response.status_code == 429:
                    return None
                last_error = f"HTTP {response.status_code} (client={client})"
                if response.status_code < 500:
                    break  # 4xx кроме 429: повторять бессмысленно
            self._sleep(2 ** (attempt + 1))
        raise TransportError(f"Google translate failed: {last_error}")

    @staticmethod
    def _parse(response: requests.Response) -> str:
        try:
            return "".join(seg[0] for seg in response.json()[0] if seg and seg[0])
        except (ValueError, IndexError, TypeError) as error:
            raise TransportError(f"Unexpected Google response: {error}") from error