"""Read a skills directory without giving its metadata a second parser."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["read_skill", "read_skills"]


@dataclass(frozen=True)
class Skill:
    directory: str
    name: str
    path: Path
    description: str
    body: str
    file_bytes: int
    body_bytes: int
    model_invoked: bool
    alias_of: str | None


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) > 1 and value[:1] == value[-1:] == '"':
        return value[1:-1].replace(r'\"', '"').replace(r'\\', '\\')
    if len(value) > 1 and value[:1] == value[-1:] == "'":
        return value[1:-1].replace("''", "'")
    return value


def _fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    lines = block.splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$", lines[index])
        if not match:
            index += 1
            continue
        key, value = match.groups()
        value = value or ""
        if value in {">", ">-", ">+", "|", "|-", "|+"}:
            folded = value.startswith(">")
            parts: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index].strip() or
                                          lines[index][:1].isspace()):
                parts.append(lines[index].strip())
                index += 1
            fields[key] = (" ".join(part for part in parts if part)
                           if folded else "\n".join(parts))
            continue
        fields[key] = _scalar(value)
        index += 1
    return fields


def _metadata(text: str) -> tuple[dict[str, str], str]:
    opening = re.match(r"\s*---[ \t]*\r?\n", text)
    if not opening:
        return {}, text.strip()
    closing = re.search(r"^---[ \t]*(?:\r?\n|\Z)", text[opening.end():], re.M)
    if not closing:
        return {}, text.strip()
    start = opening.end()
    end = start + closing.start()
    return _fields(text[start:end]), text[start + closing.end():].strip()


def read_skill(path: Path) -> Skill:
    """Read one UTF-8 skill, retaining malformed frontmatter as its body."""
    path = Path(path)
    raw = path.read_bytes()
    fields, body = _metadata(raw.decode("utf-8", errors="replace"))
    directory = path.parent.name
    alias_of = fields.get("alias_of") or None
    return Skill(directory, fields.get("name") or directory, path,
                 fields.get("description", ""), body, len(raw),
                 len(body.encode("utf-8")),
                 fields.get("disable-model-invocation", "").lower() != "true",
                 alias_of)


def read_skills(root: Path) -> list[Skill]:
    """Read every direct child SKILL.md in deterministic directory order."""
    skills = []
    for path in sorted(Path(root).glob("*/SKILL.md")):
        try:
            skills.append(read_skill(path))
        except OSError:
            continue
    return skills
