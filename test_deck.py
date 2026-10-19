import tempfile
import unittest
from pathlib import Path

from deck import (CardData, build_back, build_deck, build_decks, build_front,
                  collect_cards, mask_word, write_package)


class DeckTests(unittest.TestCase):
    def test_mask_word(self):
        self.assertEqual(mask_word("to"), "..")
        self.assertEqual(mask_word("like"), "l..")
        self.assertEqual(mask_word("coffee"), "co..")

    def test_build_front_preserves_bold(self):
        display_text = "<b>Fresh roasted beans are ground</b> as baristas grind the coffee every morning."
        front = build_front(display_text, "grind the coffee", "молоть кофе")
        self.assertIn("<b>Fresh roasted beans are ground</b>", front)
        self.assertIn("gr.. .. co..", front)
        self.assertIn("(молоть кофе)", front)

    def test_build_back_preserves_bold(self):
        display_text = "<b>Fresh roasted beans are ground</b> as baristas grind the coffee every morning."
        back = build_back(display_text, "grind the coffee", "Свежие обжаренные зёрна мелют...", "hash.mp3")
        self.assertIn("<b>Fresh roasted beans are ground</b>", back)
        self.assertIn("<b>grind the coffee</b>", back)
        self.assertIn("[sound:hash.mp3]", back)

    def test_build_decks_by_topic_and_tags(self):
        cards = [
            CardData(
                sentence="Sentence 1",
                plain_sentence="Sentence 1",
                word="word1",
                hint="hint1",
                translation="перевод 1",
                audio_name="audio1.mp3",
                topic="Daily Life & Survival",
                tags=("daily_life_and_survival", "formal"),
            ),
            CardData(
                sentence="Sentence 2",
                plain_sentence="Sentence 2",
                word="word2",
                hint="hint2",
                translation="перевод 2",
                audio_name="audio2.mp3",
                topic="Business & Work",
                tags=("business_and_work", "spoken"),
            ),
        ]
        decks = build_decks("MyFile", cards)
        self.assertEqual(len(decks), 2)
        deck_names = {d.name for d in decks}
        self.assertEqual(deck_names, {"MyFile::Daily Life & Survival", "MyFile::Business & Work"})

        for deck in decks:
            for note in deck.notes:
                if deck.name == "MyFile::Daily Life & Survival":
                    self.assertEqual(note.tags, ["daily_life_and_survival", "formal"])
                else:
                    self.assertEqual(note.tags, ["business_and_work", "spoken"])

    def test_write_package_with_multiple_decks(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test.apkg"
            cards = [
                CardData(
                    sentence="Sentence 1",
                    plain_sentence="Sentence 1",
                    word="word1",
                    hint="hint1",
                    translation="перевод 1",
                    audio_name="audio1.mp3",
                    topic="Topic A",
                    tags=("tag_a",),
                ),
            ]
            decks = build_decks("TestDeck", cards)
            write_package(decks, [], out_file)
            self.assertTrue(out_file.exists())
            self.assertGreater(out_file.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()

