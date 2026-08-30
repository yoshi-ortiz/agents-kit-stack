"""Focused checks for the shared, dependency-free skill reader."""
from __future__ import annotations

import tempfile
from pathlib import Path

from skill_corpus import read_skill, read_skills


def write(root: Path, directory: str, text: str) -> Path:
    path = root / directory / "SKILL.md"
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    return path


with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    write(root, "model", "---\nname: Modelo\ndescription: >\n  Una descripción\n  con acentos: órale.\n---\n\nCuerpo con ñ.\n")
    write(root, "alias", "---\nname: otro\nalias_of: Modelo\ndisable-model-invocation: true\n---\n\nAlias.\n")
    write(root, "broken", "---\nname: unfinished\n")

    alias, broken, model = read_skills(root)
    assert [skill.directory for skill in (alias, broken, model)] == ["alias", "broken", "model"]
    assert alias.alias_of == "Modelo" and not alias.model_invoked
    assert model.description == "Una descripción con acentos: órale."
    assert model.body_bytes == len(model.body.encode("utf-8")) > len(model.body)
    assert broken.description == "" and broken.body.startswith("---")

ora = read_skill(Path(__file__).resolve().parents[2] / "ora" / "SKILL.md")
assert ora.body_bytes == len(ora.body.encode("utf-8")) > len(ora.body)

print("OK")
