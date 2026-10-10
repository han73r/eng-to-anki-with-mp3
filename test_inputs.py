import tempfile
import unittest
from pathlib import Path

from inputs import orphan_outputs, output_path, split_by_status


class InputsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.inp, self.out = root / "input", root / "output"
        self.inp.mkdir()
        self.out.mkdir()
        self.files = []
        for name in ("a", "b", "c"):
            f = self.inp / f"{name}.txt"
            f.write_text("x", encoding="utf-8")
            self.files.append(f)

    def tearDown(self):
        self._tmp.cleanup()

    def test_output_path(self):
        self.assertEqual(output_path(self.files[0], self.out), self.out / "a.apkg")

    def test_built_files_are_skipped(self):
        (self.out / "b.apkg").write_bytes(b"1")
        todo, built = split_by_status(self.files, self.out, force=False)
        self.assertEqual([f.stem for f in todo], ["a", "c"])
        self.assertEqual([f.stem for f in built], ["b"])

    def test_force_processes_everything(self):
        (self.out / "b.apkg").write_bytes(b"1")
        todo, built = split_by_status(self.files, self.out, force=True)
        self.assertEqual(len(todo), 3)
        self.assertEqual(built, [])

    def test_orphans(self):
        (self.out / "a.apkg").write_bytes(b"1")
        (self.out / "old.apkg").write_bytes(b"1")
        self.assertEqual([p.name for p in orphan_outputs(self.files, self.out)], ["old.apkg"])


if __name__ == "__main__":
    unittest.main()