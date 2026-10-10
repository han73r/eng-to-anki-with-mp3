import unittest

from chunking import make_chunks
from parsing import Sentence, parse_lines


class ParsingTests(unittest.TestCase):
    def test_parse_marked_words(self):
        s = Sentence.parse("She decided to [[look into]] the [[matter]].")
        self.assertEqual(s.text, "She decided to look into the matter.")
        self.assertEqual(s.marked_words, ("look into", "matter"))

    def test_duplicates_and_blank_lines(self):
        sentences = parse_lines(["[[a]] and [[a]]", "", "   ", "plain"])
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0].marked_words, ("a",))
        self.assertEqual(sentences[1].marked_words, ())


class ChunkingTests(unittest.TestCase):
    def test_char_limit(self):
        chunks = make_chunks(["aaaa"] * 10, max_chars=15, max_lines=100)  # по 5 символов
        self.assertTrue(all(sum(len(x) + 1 for x in c) <= 15 for c in chunks))
        self.assertEqual([x for c in chunks for x in c], ["aaaa"] * 10)

    def test_line_limit(self):
        chunks = make_chunks(list("abcdefg"), max_chars=1000, max_lines=3)
        self.assertEqual([len(c) for c in chunks], [3, 3, 1])

    def test_long_item_goes_alone_and_order_kept(self):
        items = ["x", "y" * 50, "z"]
        chunks = make_chunks(items, max_chars=10, max_lines=10)
        self.assertEqual(chunks, [["x"], ["y" * 50], ["z"]])

    def test_empty(self):
        self.assertEqual(make_chunks([], 10, 10), [])

    def test_key(self):
        chunks = make_chunks([{"t": "ab"}, {"t": "cd"}], 100, 1, key=lambda d: d["t"])
        self.assertEqual(len(chunks), 2)


if __name__ == "__main__":
    unittest.main()
