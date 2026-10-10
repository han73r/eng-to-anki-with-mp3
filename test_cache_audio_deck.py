import tempfile
import unittest
from pathlib import Path

from audio import AudioError, AudioStore
from cache import SentenceEntry, TranslationCache, WordHint
from deck import (MissingDataError, build_back, build_deck, build_front, collect_cards,
                  mask_word, write_package)
from parsing import Sentence


class CacheTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            cache = TranslationCache(path)
            e = cache.entry("Hello world.")
            e.translation = "Привет, мир."
            e.words["world"] = WordHint("мир", 'Привет, «мир».', True)
            cache.save()
            loaded = TranslationCache(path).get("Hello world.")
            self.assertEqual(loaded.translation, "Привет, мир.")
            self.assertEqual(loaded.words["world"].hint, "мир")
            self.assertTrue(loaded.is_complete(["world"]))
            self.assertFalse(loaded.is_complete(["world", "other"]))


class AudioTests(unittest.TestCase):
    def test_cache_on_disk(self):
        calls = []

        def synth(text, path):
            calls.append(text)
            path.write_bytes(b"mp3")

        with tempfile.TemporaryDirectory() as tmp:
            store = AudioStore(Path(tmp) / "a", synth=synth, delay=0, sleep=lambda s: None)
            self.assertTrue(store.ensure("Hello."))
            self.assertFalse(store.ensure("Hello."))
            self.assertEqual(calls, ["Hello."])
            self.assertTrue(store.has("Hello."))
            self.assertEqual(store.name_for("Hello."), store.name_for("Hello."))

    def test_failure_leaves_no_file(self):
        def synth(text, path):
            path.write_bytes(b"partial")
            raise RuntimeError("boom")

        with tempfile.TemporaryDirectory() as tmp:
            store = AudioStore(Path(tmp), synth=synth, delay=0, sleep=lambda s: None)
            with self.assertRaises(AudioError):
                store.ensure("Hello.")
            self.assertFalse(store.has("Hello."))


class DeckTests(unittest.TestCase):
    def test_masking(self):
        self.assertEqual(mask_word("the"), "..")
        self.assertEqual(mask_word("cat"), "c..")
        self.assertEqual(mask_word("matter"), "ma..")

    def test_front_back(self):
        self.assertEqual(build_front("I like tea.", "tea", "чай"), "I like t...<br>(чай)")
        back = build_back("I like tea.", "tea", "Я люблю чай.", "x.mp3")
        self.assertIn("<b>tea</b>", back)
        self.assertIn("[sound:x.mp3]", back)

    def test_collect_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cache = TranslationCache(tmp / "c.json")
            store = AudioStore(tmp / "a", synth=lambda t, p: p.write_bytes(b"mp3"),
                               delay=0, sleep=lambda s: None)
            s = Sentence.parse("I [[like]] green [[tea]].")

            with self.assertRaises(MissingDataError):          # ничего ещё нет
                collect_cards([s], cache, store)

            e = cache.entry(s.text)
            e.translation = "Я люблю зелёный чай."
            e.words["like"] = WordHint("люблю", "", True)
            e.words["tea"] = WordHint("чай", "", True)
            with self.assertRaises(MissingDataError):          # нет аудио
                collect_cards([s], cache, store)

            store.ensure(s.text)
            cards = collect_cards([s], cache, store)
            self.assertEqual(len(cards), 2)

            out = tmp / "deck.apkg"
            write_package(build_deck("deck", cards), [store.path_for(s.text)], out)
            self.assertGreater(out.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
