"""Блок 6. Озвучка с дисковым кэшем (audio_cache/<hash>.mp3)."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Callable

from config import AUDIO_DELAY_SEC


class AudioError(Exception):
    pass


def default_synth(text: str, path: Path) -> None:
    from gtts import gTTS
    gTTS(text=text, lang="en").save(str(path))


class AudioStore:
    def __init__(
        self,
        directory: Path,
        synth: Callable[[str, Path], None] = default_synth,
        delay: float = AUDIO_DELAY_SEC,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._dir = directory
        self._synth = synth
        self._delay = delay
        self._sleep = sleep

    def name_for(self, text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16] + ".mp3"

    def path_for(self, text: str) -> Path:
        return self._dir / self.name_for(text)

    def has(self, text: str) -> bool:
        path = self.path_for(text)
        return path.exists() and path.stat().st_size > 0

    def ensure(self, text: str) -> bool:
        """Озвучить, если файла ещё нет. True, если был сделан запрос."""
        if self.has(text):
            return False
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(text)
        tmp = path.with_suffix(".tmp")
        try:
            self._synth(text, tmp)
            tmp.replace(path)
        except Exception as error:
            tmp.unlink(missing_ok=True)
            raise AudioError(f"TTS failed for '{text}': {error}") from error
        self._sleep(self._delay)
        return True
