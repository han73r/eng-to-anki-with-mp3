import tempfile
import unittest
from pathlib import Path

from config import TARGET_SENTENCE_COUNT
from parsing import (Sentence, clean_markdown_bold, normalize_tag, parse_lines,
                     read_sentences, render_markdown_bold,
                     validate_target_counts)


class ParsingTests(unittest.TestCase):
    def test_normalize_tag(self):
        self.assertEqual(normalize_tag("[Daily Life & Survival]"), "daily_life_and_survival")
        self.assertEqual(normalize_tag("Formal"), "formal")
        self.assertEqual(normalize_tag("Present Continuous"), "present_continuous")
        self.assertEqual(normalize_tag("Advanced Passive"), "advanced_passive")
        self.assertEqual(normalize_tag("C1"), "c1")
        self.assertEqual(normalize_tag("  Multiple   Spaces  &  Symbols!  "), "multiple_spaces_and_symbols")

    def test_markdown_bold(self):
        text = "**Fresh roasted beans are ground** as baristas grind the coffee."
        self.assertEqual(
            clean_markdown_bold(text),
            "Fresh roasted beans are ground as baristas grind the coffee.",
        )
        self.assertEqual(
            render_markdown_bold(text),
            "<b>Fresh roasted beans are ground</b> as baristas grind the coffee.",
        )

    def test_parse_multi_field_line(self):
        line = (
            "grind the coffee | [Daily Life & Survival] | Formal | Present Continuous | "
            "Advanced Passive | **Fresh roasted beans are ground** as baristas [[grind the coffee]] every morning."
        )
        s = Sentence.parse(line)
        self.assertEqual(s.target, "grind the coffee")
        self.assertEqual(s.topic, "daily_life_and_survival")
        self.assertEqual(
            s.tags,
            ("daily_life_and_survival", "formal", "present_continuous", "advanced_passive"),
        )
        self.assertEqual(
            s.text,
            "Fresh roasted beans are ground as baristas grind the coffee every morning.",
        )
        self.assertEqual(
            s.display_text,
            "<b>Fresh roasted beans are ground</b> as baristas grind the coffee every morning.",
        )
        self.assertEqual(s.marked_words, ("grind the coffee",))

    def test_parse_variable_topic_position(self):
        line1 = (
            "infringement of my human rights | chunk | C1 | [Business & Economics] | Neutral | "
            "Future Simple | The court [[will rule on this infringement of my human rights]] next month."
        )
        s1 = Sentence.parse(line1)
        self.assertEqual(s1.target, "infringement of my human rights")
        self.assertEqual(s1.topic, "business_and_economics")
        self.assertEqual(
            s1.tags,
            ("chunk", "c1", "business_and_economics", "neutral", "future_simple"),
        )

        line2 = (
            "unauthorized access beyond this point | chunk | B2 | [IT & Software] | Neutral | "
            "Future Continuous | Automated firewalls [[will be preventing unauthorized access beyond this point]] after the update."
        )
        s2 = Sentence.parse(line2)
        self.assertEqual(s2.target, "unauthorized access beyond this point")
        self.assertEqual(s2.topic, "it_and_software")
        self.assertIn("it_and_software", s2.tags)

        line3 = (
            "Do you have the authority to do that? | pattern | B1 | [Behavioral & Work] | Spoken | "
            "Past Continuous | I was wondering, \"[[Do you have the authority to do that?]]\", during the meeting."
        )
        s3 = Sentence.parse(line3)
        self.assertEqual(s3.target, "Do you have the authority to do that?")
        self.assertEqual(s3.topic, "behavioral_and_work")
        self.assertIn("behavioral_and_work", s3.tags)

    def test_parse_legacy_single_field_line(self):
        line = "She decided to [[look into]] the matter."
        s = Sentence.parse(line)
        self.assertEqual(s.target, "")
        self.assertEqual(s.topic, "")
        self.assertEqual(s.tags, ())
        self.assertEqual(s.text, "She decided to look into the matter.")
        self.assertEqual(s.display_text, "She decided to look into the matter.")
        self.assertEqual(s.marked_words, ("look into",))

    def test_validate_target_counts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            report_file = Path(tmp_dir) / "bad_word_rows.txt"
            sentences = [
                Sentence(text="1", marked_words=("a",), target="target_a"),
                Sentence(text="2", marked_words=("a",), target="target_a"),
                Sentence(text="3", marked_words=("a",), target="target_a"),
                Sentence(text="4", marked_words=("b",), target="target_b"),
                Sentence(text="5", marked_words=("b",), target="target_b"),
            ]
            warnings = []
            bad = validate_target_counts(sentences, report_path=report_file, log_fn=warnings.append)
            self.assertEqual(bad, ["target_b"])
            self.assertTrue(report_file.exists())
            content = report_file.read_text(encoding="utf-8")
            self.assertIn("Target 'target_b': 2 rows (expected 3)", content)
            self.assertTrue(any("target_b" in w for w in warnings))

    def test_read_sentences_with_row_limit(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "test.txt"
            report_file = Path(tmp_dir) / "bad.txt"
            lines = [
                f"word{i//3} | [Topic] | Tag | Sentence [[word{i//3}]] {i}."
                for i in range(15)
            ]
            input_file.write_text("\n".join(lines), encoding="utf-8")

            sentences = read_sentences(input_file, max_rows=6, report_path=report_file, validate=False)
            self.assertEqual(len(sentences), 6)
            self.assertEqual(len({s.target for s in sentences}), 2)


if __name__ == "__main__":
    unittest.main()

