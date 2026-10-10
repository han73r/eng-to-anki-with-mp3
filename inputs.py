"""Соответствие input/*.txt <-> output/*.apkg. Без сети."""
from __future__ import annotations

from pathlib import Path


def output_path(input_path: Path, output_dir: Path) -> Path:
    return output_dir / (input_path.stem + ".apkg")


def split_by_status(
    files: list[Path], output_dir: Path, force: bool
) -> tuple[list[Path], list[Path]]:
    """(что обработать, что пропустить как уже собранное)."""
    todo: list[Path] = []
    built: list[Path] = []
    for f in files:
        done = not force and output_path(f, output_dir).exists()
        (built if done else todo).append(f)
    return todo, built


def orphan_outputs(input_files: list[Path], output_dir: Path) -> list[Path]:
    """.apkg в output/, для которых в input/ уже нет .txt."""
    stems = {f.stem for f in input_files}
    return sorted(p for p in output_dir.glob("*.apkg") if p.stem not in stems)