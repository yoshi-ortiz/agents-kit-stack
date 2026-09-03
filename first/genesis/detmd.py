#!/usr/bin/env python3
"""Deterministic mirrors for declared Markdown tables and fences."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

__version__ = "0.1.0"

MARKER = re.compile(r"\s*<!--\s*detmd\s+(\{.*\})\s*-->\s*(?:\n)?$")
KINDS = {"string", "integer", "boolean", "null", "id", "ref"}
DIRECTIONS = {"source-to-markdown", "markdown-with-derived", "markdown-to-runtime"}
OPS = {"project", "sort", "join", "count", "sum", "bytes_si", "bytes_iec",
       "unique", "foreign_key"}


class DetmdError(RuntimeError):
    """A declaration cannot be evaluated safely or deterministically."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Issue:
    code: str
    declaration_id: str | None
    path: Path
    line: int
    message: str
    expected: str | None = None
    actual: str | None = None


@dataclass(frozen=True)
class RenderResult:
    declaration_id: str
    path: Path
    changed: bool
    canonical_sha256: str
    render_sha256: str


@dataclass(frozen=True)
class _Declaration:
    spec: dict[str, Any]
    path: Path
    root: Path
    line: int
    start: int
    end: int
    block: str

    @property
    def identifier(self) -> str:
        return str(self.spec.get("id") or "")


def _digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _files(paths: Iterable[str | os.PathLike[str]]) -> list[tuple[Path, Path]]:
    found: dict[Path, Path] = {}
    for raw in paths:
        path = Path(raw).resolve()
        if path.is_file():
            if path.suffix in {".md", ".txt"}:
                found.setdefault(path, Path.cwd().resolve())
            continue
        if not path.is_dir():
            continue
        for base, dirs, names in os.walk(path):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for name in sorted(names):
                candidate = Path(base, name)
                if candidate.suffix in {".md", ".txt"}:
                    found.setdefault(candidate.resolve(), path)
    return sorted(found.items())


def _block(lines: list[str], index: int, path: Path) -> tuple[int, str]:
    if index >= len(lines):
        raise DetmdError("missing-block", f"{path}: declaration has no following block")
    first = lines[index]
    if first.startswith("|"):
        end = index
        while end < len(lines) and lines[end].startswith("|"):
            end += 1
        if end - index < 2:
            raise DetmdError("bad-table", f"{path}: managed table needs a header and separator")
        return end, "".join(lines[index:end])
    if first.startswith("```"):
        fence = first[:len(first) - len(first.lstrip("`"))]
        end = index + 1
        while end < len(lines) and not lines[end].startswith(fence):
            end += 1
        if end == len(lines):
            raise DetmdError("bad-fence", f"{path}: managed fence is not closed")
        return end + 1, "".join(lines[index:end + 1])
    raise DetmdError("missing-block", f"{path}: declaration must immediately precede a table or fence")


def _scan(paths: Iterable[str | os.PathLike[str]]) -> tuple[list[_Declaration], list[Issue]]:
    declarations: list[_Declaration] = []
    issues: list[Issue] = []
    for path, root in _files(paths):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        offsets: list[int] = []
        cursor = 0
        for line in lines:
            offsets.append(cursor)
            cursor += len(line)
        for index, line in enumerate(lines):
            if "<!-- detmd" not in line:
                continue
            match = MARKER.fullmatch(line)
            if not match:
                issues.append(Issue("bad-declaration", None, path, index + 1,
                                    "detmd declaration must be one valid JSON comment"))
                continue
            try:
                spec = json.loads(match.group(1))
                if not isinstance(spec, dict):
                    raise ValueError("declaration is not an object")
                end_line, raw = _block(lines, index + 1, path)
            except (json.JSONDecodeError, ValueError, DetmdError) as error:
                issues.append(Issue(getattr(error, "code", "bad-declaration"),
                                    None, path, index + 1, str(error)))
                continue
            start = offsets[index + 1]
            end = offsets[end_line] if end_line < len(offsets) else len(text)
            declarations.append(_Declaration(spec, path, root, index + 1,
                                             start, end, raw))
    seen: dict[str, _Declaration] = {}
    for declaration in declarations:
        identifier = declaration.identifier
        if identifier in seen:
            issues.append(Issue("duplicate-id", identifier, declaration.path,
                                declaration.line, f"detmd id {identifier!r} is already declared"))
        seen[identifier] = declaration
    return declarations, issues


def _path(root: Path, raw: Any) -> Path:
    if not isinstance(raw, str) or not raw:
        raise DetmdError("bad-source", "source path must be a non-empty string")
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise DetmdError("escaped-root", f"source path escapes declared root: {raw}") from error
    if not path.is_file():
        raise DetmdError("missing-source", f"source does not exist: {raw}")
    return path


def _no_floats(value: Any) -> None:
    if isinstance(value, float):
        raise DetmdError("float", "floating-point values are forbidden")
    if isinstance(value, Mapping):
        for child in value.values():
            _no_floats(child)
    elif isinstance(value, list):
        for child in value:
            _no_floats(child)


def _pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise DetmdError("bad-pointer", "JSON Pointer must be empty or start with /")
    current = value
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        try:
            current = current[int(token)] if isinstance(current, list) else current[token]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise DetmdError("bad-pointer", f"JSON Pointer has no token {token!r}") from error
    return current


def _coerce(raw: str, kind: str, nullable: bool = False) -> Any:
    if raw == "" and nullable:
        return None
    if kind == "integer":
        if not re.fullmatch(r"-?(0|[1-9][0-9]*)", raw):
            raise DetmdError("bad-type", f"{raw!r} is not an integer")
        return int(raw)
    if kind == "boolean":
        if raw not in {"true", "false"}:
            raise DetmdError("bad-type", f"{raw!r} is not true or false")
        return raw == "true"
    if kind == "null":
        if raw not in {"", "null"}:
            raise DetmdError("bad-type", f"{raw!r} is not null")
        return None
    return raw


_EXPORTER = r"""
import importlib.util, json, pathlib, re, sys
path, function = pathlib.Path(sys.argv[1]), sys.argv[2]
if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', function):
    raise SystemExit('invalid exporter function')
sys.path.insert(0, str(path.parent))
def confined(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.posix_spawn'}:
        raise PermissionError('detmd exporters cannot access the network or launch commands')
sys.addaudithook(confined)
spec = importlib.util.spec_from_file_location('_detmd_source', path)
if spec is None or spec.loader is None:
    raise SystemExit('cannot load exporter')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
json.dump(getattr(module, function)(), sys.stdout, ensure_ascii=False,
          sort_keys=True, separators=(',', ':'), allow_nan=False)
"""


def _source(alias: str, spec: Mapping[str, Any], root: Path) -> tuple[Any, dict[str, str]]:
    kind = spec.get("kind")
    path = _path(root, spec.get("path"))
    digest = _digest(path.read_bytes())
    if kind == "json":
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise DetmdError("bad-json", f"{path}: {error}") from error
        value = _pointer(value, str(spec.get("pointer", "")))
    elif kind == "tsv":
        with path.open(encoding="utf-8", newline="") as handle:
            value = list(csv.DictReader(handle, delimiter="\t"))
        types = spec.get("types", {})
        if not isinstance(types, dict) or any(kind not in KINDS for kind in types.values()):
            raise DetmdError("bad-source", f"{alias}: invalid TSV types")
        value = [{key: _coerce(raw, types.get(key, "string"))
                  for key, raw in row.items()} for row in value]
    elif kind == "python-export":
        function = spec.get("function")
        if not isinstance(function, str):
            raise DetmdError("bad-source", f"{alias}: exporter function is required")
        try:
            done = subprocess.run(
                [sys.executable, "-I", "-c", _EXPORTER, str(path), function],
                cwd=root, env={"PYTHONIOENCODING": "utf-8"},
                capture_output=True, text=True, timeout=5,
            )
        except subprocess.TimeoutExpired as error:
            raise DetmdError("source-timeout", f"{alias}: exporter exceeded 5 seconds") from error
        if done.returncode:
            detail = done.stderr.strip().splitlines()[-1] if done.stderr.strip() else "failed"
            raise DetmdError("source", f"{alias}: exporter {detail}")
        try:
            value = json.loads(done.stdout)
        except json.JSONDecodeError as error:
            raise DetmdError("source", f"{alias}: exporter did not emit one JSON value") from error
    else:
        raise DetmdError("bad-source", f"{alias}: unsupported source kind {kind!r}")
    _no_floats(value)
    return value, {"alias": alias, "kind": str(kind),
                   "path": str(path.relative_to(root)), "sha256": digest}


def _split_row(line: str) -> list[str]:
    line = line.rstrip("\r\n")
    if not line.startswith("|") or not line.endswith("|"):
        raise DetmdError("bad-table", "managed pipe rows must start and end with |")
    cells: list[str] = []
    cell: list[str] = []
    escaped = False
    for char in line[1:-1]:
        if escaped:
            if char not in {"|", "\\"}:
                cell.append("\\")
            cell.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(char)
    if escaped:
        cell.append("\\")
    cells.append("".join(cell).strip())
    return cells


def _markdown_rows(block: str, columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines = block.splitlines()
    if len(lines) < 2:
        raise DetmdError("bad-table", "managed table needs a header and separator")
    names = _split_row(lines[0])
    separators = _split_row(lines[1])
    if len(names) != len(separators) or any(not re.fullmatch(r":?-{3,}:?", item)
                                            for item in separators):
        raise DetmdError("bad-table", "managed table separator is invalid")
    inputs = {column["name"]: column for column in columns
              if column.get("role", "input") != "derived"}
    if set(inputs) - set(names):
        raise DetmdError("bad-table", "managed table is missing an input column")
    rows: list[dict[str, Any]] = []
    for line in lines[2:]:
        values = _split_row(line)
        if len(values) != len(names):
            raise DetmdError("bad-table", "managed table row has the wrong cell count")
        raw = dict(zip(names, values))
        rows.append({name: _coerce(raw[name], column["type"], column.get("nullable", False))
                     for name, column in inputs.items()})
    return rows


def _validate_spec(spec: Mapping[str, Any], block: str) -> list[dict[str, Any]]:
    allowed = {"version", "id", "direction", "sources", "from", "schema", "key",
               "order_by", "operations", "renderer", "language", "execution"}
    unknown = set(spec) - allowed
    if unknown:
        raise DetmdError("bad-declaration", "unknown declaration fields: " + ", ".join(sorted(unknown)))
    if spec.get("version") != 1:
        raise DetmdError("bad-version", "detmd version must be 1")
    if not isinstance(spec.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*",
                                                               str(spec.get("id", ""))):
        raise DetmdError("bad-id", "detmd id is missing or invalid")
    if spec.get("direction") not in DIRECTIONS:
        raise DetmdError("bad-direction", "unsupported authority direction")
    if spec.get("renderer") not in {"pipe", "fence"}:
        raise DetmdError("bad-renderer", "renderer must be pipe or fence")
    columns = spec.get("schema")
    if not isinstance(columns, list):
        raise DetmdError("bad-schema", "schema must be a list")
    names: set[str] = set()
    for column in columns:
        if not isinstance(column, dict) or set(column) - {"name", "type", "role", "nullable"}:
            raise DetmdError("bad-schema", "schema column is invalid")
        name, kind = column.get("name"), column.get("type")
        if not isinstance(name, str) or not name or name in names or kind not in KINDS:
            raise DetmdError("bad-schema", "schema names must be unique and types supported")
        if column.get("role", "input") not in {"input", "derived"}:
            raise DetmdError("bad-schema", f"{name}: role must be input or derived")
        names.add(name)
    for field in ("key", "order_by"):
        value = spec.get(field, [])
        if not isinstance(value, list) or any(item not in names for item in value):
            raise DetmdError("bad-schema", f"{field} must name schema columns")
    operations = spec.get("operations", [])
    if not isinstance(operations, list) or any(not isinstance(op, dict) or op.get("op") not in OPS
                                                for op in operations):
        raise DetmdError("bad-operation", "operation is missing or unsupported")
    if spec["direction"] == "markdown-with-derived" and spec["renderer"] != "pipe":
        raise DetmdError("bad-direction", "editable Markdown requires the pipe renderer")
    if spec["direction"] == "markdown-to-runtime":
        if spec["renderer"] != "fence" or not isinstance(spec.get("execution"), dict):
            raise DetmdError("bad-execution", "runtime fences require an execution declaration")
        execution = spec["execution"]
        required = {"runner", "cwd", "timeout_seconds", "expected_exit", "inputs", "outputs"}
        if set(execution) != required:
            raise DetmdError("bad-execution", "execution declaration fields are incomplete or unknown")
        paths_ok = all(isinstance(execution[name], list)
                       and all(isinstance(path, str) for path in execution[name])
                       for name in ("inputs", "outputs"))
        if (not isinstance(execution["runner"], str) or not execution["runner"]
                or not isinstance(execution["cwd"], str) or not execution["cwd"]
                or not isinstance(execution["timeout_seconds"], int)
                or isinstance(execution["timeout_seconds"], bool)
                or execution["timeout_seconds"] <= 0
                or not isinstance(execution["expected_exit"], int)
                or isinstance(execution["expected_exit"], bool) or not paths_ok):
            raise DetmdError("bad-execution", "execution declaration has invalid field types")
    if spec["renderer"] == "pipe" and not block.startswith("|"):
        raise DetmdError("bad-table", "pipe renderer must own a table")
    if spec["renderer"] == "fence" and not block.startswith("```"):
        raise DetmdError("bad-fence", "fence renderer must own a fence")
    return columns


def _rows(value: Any, alias: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise DetmdError("bad-source", f"{alias}: tabular source must be a list of objects")
    return [dict(row) for row in value]


def _sort(rows: list[dict[str, Any]], fields: Sequence[str]) -> list[dict[str, Any]]:
    try:
        return sorted(rows, key=lambda row: tuple((row.get(name) is None, row.get(name))
                                                  for name in fields))
    except TypeError as error:
        raise DetmdError("bad-type", "sort values have incompatible types") from error


def _groups(rows: list[dict[str, Any]], fields: Sequence[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = tuple(row.get(field) for field in fields)
        grouped.setdefault(key, []).append(row)
    return grouped


def _operations(rows: list[dict[str, Any]], sources: Mapping[str, list[dict[str, Any]]],
                operations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    current = rows
    for operation in operations:
        name = operation["op"]
        if name == "project":
            fields = operation.get("columns", [])
            current = [{field: row.get(field) for field in fields} for row in current]
        elif name == "sort":
            current = _sort(current, operation.get("by", []))
        elif name == "join":
            right_name = operation.get("source")
            if right_name not in sources:
                raise DetmdError("bad-operation", f"join source {right_name!r} is missing")
            pairs = operation.get("on", [])
            if not pairs or any(not isinstance(pair, list) or len(pair) != 2 for pair in pairs):
                raise DetmdError("bad-operation", "join needs [left, right] key pairs")
            index: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
            for right in sources[right_name]:
                index.setdefault(tuple(right.get(pair[1]) for pair in pairs), []).append(right)
            joined: list[dict[str, Any]] = []
            for left in current:
                matches = index.get(tuple(left.get(pair[0]) for pair in pairs), [])
                if not matches and operation.get("how", "inner") == "left":
                    matches = [{}]
                for right in matches:
                    merged = dict(left)
                    for key, value in right.items():
                        if key in merged and merged[key] != value:
                            raise DetmdError("join-collision", f"join changes existing column {key!r}")
                        merged[key] = value
                    joined.append(merged)
            current = joined
        elif name in {"count", "sum"}:
            group_by = operation.get("group_by", [])
            output = operation.get("as")
            if not isinstance(output, str):
                raise DetmdError("bad-operation", f"{name} needs an output column")
            aggregated: list[dict[str, Any]] = []
            for key, members in _groups(current, group_by).items():
                row = dict(zip(group_by, key))
                if name == "count":
                    row[output] = len(members)
                else:
                    column = operation.get("column")
                    values = [member.get(column) for member in members]
                    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
                        raise DetmdError("bad-type", f"sum column {column!r} is not integer")
                    row[output] = sum(values)
                aggregated.append(row)
            current = aggregated
        elif name in {"bytes_si", "bytes_iec"}:
            base = 1000 if name == "bytes_si" else 1024
            units = (["B", "kB", "MB", "GB", "TB"] if base == 1000
                     else ["B", "KiB", "MiB", "GiB", "TiB"])
            unit, places = operation.get("unit"), operation.get("places", 0)
            if unit not in units or not isinstance(places, int) or not 0 <= places <= 9:
                raise DetmdError("bad-operation", f"{name} has an invalid unit or precision")
            column, output = operation.get("column"), operation.get("as")
            factor = Decimal(base) ** units.index(unit)
            quantum = Decimal(1).scaleb(-places)
            for row in current:
                value = row.get(column)
                if not isinstance(value, int) or isinstance(value, bool):
                    raise DetmdError("bad-type", f"byte column {column!r} is not integer")
                converted = (Decimal(value) / factor).quantize(quantum, rounding=ROUND_HALF_UP)
                row[output] = f"{converted:.{places}f} {unit}"
        elif name == "unique":
            fields = operation.get("columns", [])
            values = [tuple(row.get(field) for field in fields) for row in current]
            if len(values) != len(set(values)):
                raise DetmdError("duplicate-key", f"columns {fields!r} are not unique")
        elif name == "foreign_key":
            source = operation.get("source")
            if source not in sources:
                raise DetmdError("bad-operation", f"foreign-key source {source!r} is missing")
            column, target = operation.get("column"), operation.get("target")
            allowed = {row.get(target) for row in sources[source]}
            missing = [row.get(column) for row in current if row.get(column) not in allowed]
            if missing:
                raise DetmdError("broken-reference", f"{column} has missing references: {missing!r}")
    return current


def _value_ok(value: Any, column: Mapping[str, Any]) -> bool:
    if value is None:
        return column.get("nullable", False) or column["type"] == "null"
    kind = column["type"]
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return False
    if kind in {"string", "id", "ref"}:
        return isinstance(value, str) and (kind == "string" or bool(value))
    return False


def _normalize(declaration: _Declaration) -> tuple[Any, list[dict[str, str]]]:
    spec = declaration.spec
    columns = _validate_spec(spec, declaration.block)
    if spec["direction"] == "markdown-to-runtime":
        return declaration.block, []
    if spec["direction"] == "markdown-with-derived":
        raw_sources: dict[str, Any] = {"main": _markdown_rows(declaration.block, columns)}
        provenance = [{"alias": "main", "kind": "markdown", "path": str(declaration.path),
                       "sha256": _digest(_json(raw_sources["main"]))}]
    else:
        raw_sources = {}
        provenance = []
    sources = spec.get("sources", {})
    if not isinstance(sources, dict):
        raise DetmdError("bad-source", "sources must be an object")
    for alias, source_spec in sources.items():
        if not isinstance(source_spec, dict):
            raise DetmdError("bad-source", f"{alias}: source must be an object")
        raw_sources[alias], evidence = _source(alias, source_spec, declaration.root)
        provenance.append(evidence)
    main = spec.get("from", "main")
    if main not in raw_sources:
        raise DetmdError("bad-source", f"initial source {main!r} is missing")
    if spec["renderer"] == "fence":
        value = raw_sources[main]
        if not isinstance(value, str):
            raise DetmdError("bad-source", "fence source must resolve to text")
        return value, provenance
    typed_sources = {alias: _rows(value, alias) for alias, value in raw_sources.items()}
    rows = _operations([dict(row) for row in typed_sources[main]], typed_sources,
                       spec.get("operations", []))
    output: list[dict[str, Any]] = []
    for row in rows:
        normalized: dict[str, Any] = {}
        for column in columns:
            name = column["name"]
            value = row.get(name)
            if not _value_ok(value, column):
                raise DetmdError("bad-type", f"{name}: value {value!r} does not match {column['type']}")
            normalized[name] = value
        output.append(normalized)
    key = spec.get("key", [])
    keys = [tuple(row[name] for name in key) for row in output]
    if key and len(keys) != len(set(keys)):
        raise DetmdError("duplicate-key", f"key {key!r} is not unique")
    return _sort(output, spec.get("order_by", [])), provenance


def _cell(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    text = str(value)
    if "\n" in text or "\r" in text:
        raise DetmdError("multiline-cell", "pipe cells cannot contain newlines")
    return text.replace("\\", "\\\\").replace("|", "\\|")


def _pipe(rows: list[dict[str, Any]], columns: Sequence[Mapping[str, Any]]) -> str:
    names = [column["name"] for column in columns]
    lines = ["| " + " | ".join(names) + " |",
             "| " + " | ".join("---" for _ in names) + " |"]
    lines.extend("| " + " | ".join(_cell(row[name]) for name in names) + " |"
                 for row in rows)
    return "\n".join(lines) + "\n"


def _tsv(rows: list[dict[str, Any]], columns: Sequence[Mapping[str, Any]]) -> str:
    names = [column["name"] for column in columns]
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(names)
    writer.writerows(["null" if row[name] is None else
                      "true" if row[name] is True else
                      "false" if row[name] is False else row[name] for name in names]
                     for row in rows)
    return output.getvalue()


def _prepared(declaration: _Declaration) -> tuple[Any, str, dict[str, Any]]:
    value, sources = _normalize(declaration)
    spec = declaration.spec
    if spec["direction"] == "markdown-to-runtime":
        rendered = declaration.block
    elif spec["renderer"] == "fence":
        language = spec.get("language", "")
        rendered = f"```{language}\n{str(value).rstrip()}\n```\n"
    else:
        rendered = _pipe(value, spec["schema"])
    canonical = {"detmd": 1, "id": spec["id"], "schema": spec["schema"],
                 "rows": value if isinstance(value, list) else None}
    if not isinstance(value, list):
        canonical["value"] = value
    canonical_sha = _digest(_json(canonical))
    envelope = {**canonical, "provenance": {
        "canonical_sha256": canonical_sha,
        "engine": __version__,
        "operations": spec.get("operations", []),
        "render_sha256": _digest(rendered),
        "sources": sources,
    }}
    return value, rendered, envelope


def _selected(paths: Iterable[str | os.PathLike[str]], ids: Collection[str]) -> tuple[list[_Declaration], list[Issue]]:
    declarations, issues = _scan(paths)
    wanted = set(ids)
    if wanted:
        found = {declaration.identifier for declaration in declarations}
        for missing in sorted(wanted - found):
            issues.append(Issue("missing-id", missing, Path("."), 0,
                                f"detmd id {missing!r} was not found"))
        declarations = [declaration for declaration in declarations
                        if declaration.identifier in wanted]
    return declarations, issues


def check(paths: Sequence[str | os.PathLike[str]] = (".",),
          ids: Collection[str] = ()) -> tuple[Issue, ...]:
    """Return every declaration, source, validation, and drift problem."""
    declarations, issues = _selected(paths, ids)
    for declaration in declarations:
        try:
            _, rendered, _ = _prepared(declaration)
        except DetmdError as error:
            issues.append(Issue(error.code, declaration.identifier, declaration.path,
                                declaration.line, str(error)))
            continue
        if rendered != declaration.block:
            issues.append(Issue("drift", declaration.identifier, declaration.path,
                                declaration.line, "managed region differs from deterministic state",
                                rendered, declaration.block))
    return tuple(issues)


def render(paths: Sequence[str | os.PathLike[str]] = (".",),
           ids: Collection[str] = ()) -> tuple[RenderResult, ...]:
    """Atomically repair selected managed regions, one document at a time."""
    declarations, issues = _selected(paths, ids)
    if issues:
        issue = issues[0]
        raise DetmdError(issue.code, issue.message)
    grouped: dict[Path, list[_Declaration]] = {}
    for declaration in declarations:
        grouped.setdefault(declaration.path, []).append(declaration)
    results: list[RenderResult] = []
    for path, owned in grouped.items():
        prepared: list[tuple[_Declaration, str, dict[str, Any]]] = []
        for declaration in owned:
            _, block, envelope = _prepared(declaration)
            prepared.append((declaration, block, envelope))
        original = path.read_text(encoding="utf-8")
        updated = original
        for declaration, block, _ in sorted(prepared, key=lambda item: item[0].start,
                                             reverse=True):
            updated = updated[:declaration.start] + block + updated[declaration.end:]
        changed = updated != original
        if changed:
            descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                    handle.write(updated)
                os.chmod(temp_name, stat.S_IMODE(path.stat().st_mode))
                os.replace(temp_name, path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        for declaration, _, envelope in prepared:
            provenance = envelope["provenance"]
            results.append(RenderResult(declaration.identifier, path, changed,
                                        provenance["canonical_sha256"],
                                        provenance["render_sha256"]))
    return tuple(results)


def export(identifier: str, paths: Sequence[str | os.PathLike[str]] = (".",),
           format: str = "json") -> str:
    """Export one declared mirror as canonical JSON, a pipe table, or TSV."""
    declarations, issues = _selected(paths, (identifier,))
    if issues:
        raise DetmdError(issues[0].code, issues[0].message)
    if len(declarations) != 1:
        raise DetmdError("missing-id", f"detmd id {identifier!r} was not found")
    declaration = declarations[0]
    value, rendered, envelope = _prepared(declaration)
    if format == "json":
        return _json(envelope) + "\n"
    if not isinstance(value, list):
        raise DetmdError("bad-format", "pipe and TSV exports require tabular state")
    if format == "pipe":
        return rendered if declaration.spec["renderer"] == "pipe" else _pipe(value, declaration.spec["schema"])
    if format == "tsv":
        return _tsv(value, declaration.spec["schema"])
    raise DetmdError("bad-format", f"unsupported export format {format!r}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="detmd", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("check", "report invalid or stale declared mirrors"),
                            ("render", "repair declared mirrors")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("paths", nargs="*", default=["."])
        command.add_argument("--id", action="append", default=[])
    command = sub.add_parser("export", help="export one declared mirror")
    command.add_argument("identifier")
    command.add_argument("paths", nargs="*", default=["."])
    command.add_argument("--format", required=True, choices=("json", "pipe", "tsv"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            issues = check(args.paths, args.id)
            for issue in issues:
                print(f"{issue.path}:{issue.line}: {issue.code}: {issue.message}", file=sys.stderr)
            return 1 if issues else 0
        if args.command == "render":
            for result in render(args.paths, args.id):
                print(f"{'rendered' if result.changed else 'ok'} {result.declaration_id} {result.path}")
            return 0
        sys.stdout.write(export(args.identifier, args.paths, args.format))
        return 0
    except (DetmdError, OSError, UnicodeError) as error:
        print(f"error: {getattr(error, 'code', type(error).__name__)}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
