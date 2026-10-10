import tempfile
import unittest
from pathlib import Path

from cache import TranslationCache
from parsing import Sentence
from translation import (Translator, extract_hint, looks_like_junk, match_case,
                         quote_word)


class EchoTransport:
    """Фейковый Google: каждую строку превращает в 'RU <строка>', кавычки сохраняет."""
    def __init__(self):
        self.calls: list[str] = []

    def translate(self, text):
        self.calls.append(text)
        return "\n".join(f"RU {line}" for line in text.split("\n"))


class MergingTransport(EchoTransport):
    """Ломается на многострочных запросах: склеивает всё в одну строку."""
    def translate(self, text):
        self.calls.append(text)
        lines = text.split("\n")
        if len(lines) > 1:
            return "RU " + " ".join(lines)
        return f"RU {text}"


class QuoteStrippingTransport(EchoTransport):
    """Теряет кавычки (как плохой переводчик)."""
    def translate(self, text):
        return super().translate(text.replace('"', ""))


def make_translator(transport, cache, **kwargs):
    return Translator(transport, cache, delay=0, sleep=lambda s: None, log=lambda m: None, **kwargs)


class PureFunctionTests(unittest.TestCase):
    def test_quote_word(self):
        self.assertEqual(quote_word("She likes cats.", "cats"), 'She likes "cats".')
        self.assertIsNone(quote_word("She likes cats.", "dogs"))
        self.assertEqual(quote_word("a cat in a category", "cat"), 'a "cat" in a category')

    def test_extract_hint(self):
        self.assertEqual(extract_hint('Она любит «кошек».', "cats", "She likes cats."), "кошек")
        self.assertEqual(extract_hint('Она любит "кошек".', "cats", "She likes cats."), "кошек")
        self.assertIsNone(extract_hint("Она любит кошек.", "cats", "She likes cats."))

    def test_junk(self):
        self.assertTrue(looks_like_junk("ПРИВЕТ МИР"))
        self.assertTrue(looks_like_junk("abc 123"))
        self.assertFalse(looks_like_junk("кошка"))

    def test_match_case(self):
        self.assertEqual(match_case("Кошка", "cat", "The cat sat."), "кошка")
        self.assertEqual(match_case("Лондон", "London", "I love London."), "Лондон")


class TranslatorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache_path = Path(self._tmp.name) / "cache.json"
        self.cache = TranslationCache(self.cache_path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fills_cache_in_one_chunk(self):
        transport = EchoTransport()
        s = Sentence.parse("She decided to [[look into]] the matter.")
        make_translator(transport, self.cache).run([s])

        self.assertEqual(len(transport.calls), 1)
        entry = TranslationCache(self.cache_path).get(s.text)   # читаем с диска
        self.assertEqual(entry.translation, "RU She decided to look into the matter.")
        hint = entry.words["look into"]
        self.assertEqual(hint.hint, "look into")
        self.assertTrue(hint.in_context)
        self.assertIn('"look into"', hint.raw)

    def test_cached_not_resent(self):
        transport = EchoTransport()
        s = Sentence.parse("I [[like]] tea.")
        make_translator(transport, self.cache).run([s])
        make_translator(transport, self.cache).run([s])
        self.assertEqual(len(transport.calls), 1)

    def test_new_word_sends_only_that_word(self):
        transport = EchoTransport()
        make_translator(transport, self.cache).run([Sentence.parse("I [[like]] green tea.")])
        make_translator(transport, self.cache).run([Sentence.parse("I [[like]] [[green]] tea.")])
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(transport.calls[1], 'I like "green" tea.')

    def test_line_count_mismatch_splits(self):
        transport = MergingTransport()
        sentences = [Sentence.parse(f"Sentence [[number]] {i}.") for i in range(3)]
        make_translator(transport, self.cache).run(sentences)
        for s in sentences:
            entry = self.cache.get(s.text)
            self.assertTrue(entry.is_complete(s.marked_words), s.text)
            self.assertEqual(entry.translation, f"RU {s.text}")

    def test_lost_quotes_use_fallback(self):
        transport = QuoteStrippingTransport()
        s = Sentence.parse("She decided to [[look into]] the matter.")
        translator = make_translator(transport, self.cache)
        translator.run([s])
        hint = self.cache.get(s.text).words["look into"]
        self.assertFalse(hint.in_context)
        self.assertEqual(hint.hint, "RU look into")
        self.assertEqual(translator.fallback_words, ["look into"])

    def test_max_chunks_limits_requests(self):
        transport = EchoTransport()
        s = Sentence.parse("I [[like]] tea.")          # 2 строки
        make_translator(transport, self.cache, max_lines=1, max_chunks=1).run([s])
        self.assertEqual(len(transport.calls), 1)

    def test_plan_makes_no_requests(self):
        translator = make_translator(None, self.cache)      # транспорта нет вообще
        jobs, fallbacks = translator.plan([Sentence.parse("I [[like]] tea.")])
        self.assertEqual([j.kind for j in jobs], ["sentence", "word"])
        self.assertEqual(fallbacks, [])


if __name__ == "__main__":
    unittest.main()
