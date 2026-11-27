#!/usr/bin/env python3
"""Audit top-level Markdown fields and emit JSON, or emit normalized Markdown with --fix.

Fields are single-line bullets such as '- Status: Open' or '- **Status:** Open'.
ATX headings scope fields. Values are returned as Markdown strings.
Use --sum or --count-ol to calculate a value and --expect to check it.
Use 'query --help' for DuckDB-backed table analytics.
Use 'tickets --help' to index ticket ids and their many-to-many links (DuckDB with --sql).
"""

import argparse
import json
import re
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

LABEL = r"[^\W\d_][^\W_]*(?:[ -]+[^\W_]+)*"
FIELD = re.compile(
    rf"^(?P<bullet>[-+*] )(?:\*\*(?P<inside>{LABEL}) *:\*\*"
    rf"|\*\*(?P<outside>{LABEL})\*\* *:|(?P<plain>{LABEL}) *:)"
    r"(?=[ \t]|$)[ \t]*(?P<value>.*)$"
)
HEADING = re.compile(r"^(#{1,6})(?:[ \t]+(.*)|$)")
FENCE = re.compile(r"^ {0,3}(?:(`{3,})[^`]*|(~{3,}).*)$")
FENCE_CLOSE = re.compile(r"^ {0,3}(`+|~+)[ \t]*$")
LIST_ITEM = re.compile(r"^(?:[-+*]|\d{1,9}[.)])(?:[ \t]|$)")
HTML_LITERAL = re.compile(r"^<(pre|script|style|textarea)(?=[\s/>]|$)", re.I)
HTML_TAG = re.compile(r"^</?[A-Za-z][\w-]*(?=[\s/>]|$)")
ORDERED_ITEM = re.compile(r"^([0-9]{1,9})([.)])(?:[ \t]+|$)")
TABLE_SEPARATOR = re.compile(r"(?<!\\)((?:\\\\)*)\|")
TABLE_ALIGNMENT = re.compile(r":?-+:?")
DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)")
THEMATIC_BREAK = re.compile(r"^(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$")


def html_end(line):
    """Return the terminator for a raw HTML block, or None for ordinary Markdown."""
    line = line.lstrip(" ")
    for start, end in (("<!--", "-->"), ("<![CDATA[", "]]>"), ("<?", "?>"), ("<!", ">")):
        if line.startswith(start):
            return end
    if match := HTML_LITERAL.match(line):
        return f"</{match[1].lower()}>"
    if HTML_TAG.match(line):
        return ""  # A blank line ends ordinary HTML blocks.
    return None


def source_lines(text):
    return re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z", text.removeprefix("\ufeff"))


def visible_lines(bodies, issue):
    start = 0
    if bodies and bodies[0] == "---":
        for start, line in enumerate(bodies[1:], 2):
            if line in ("---", "..."):
                break
        else:
            start = len(bodies)
            issue(1, "unclosed_frontmatter")

    fence = None
    raw_end = None
    for index in range(start, len(bodies)):
        line = bodies[index]
        number = index + 1
        if fence:
            closer = FENCE_CLOSE.match(line)
            if closer and closer[1].startswith(fence):
                fence = None
            continue
        if raw_end is not None:
            if (raw_end and raw_end in line.lower()) or (not raw_end and not line.strip()):
                raw_end = None
            continue
        if match := FENCE.match(line):
            fence = match[1] or match[2]
            fence_line = number
            continue
        if not line.startswith(("    ", "\t")):
            end = html_end(line)
            if end is not None:
                if not end or end not in line.lower():
                    raw_end = end
                continue
        yield index, line

    if fence:
        issue(fence_line, "unclosed_fence")


def audit(text):
    lines = source_lines(text)
    bodies = [line.rstrip("\r\n") for line in lines]
    fixed = lines.copy()
    diagnostics = []
    sections = [{"heading": [], "line": None, "values": {}}]
    headings = []
    groups = {}

    def issue(line, code, key=None):
        entry = {"line": line, "code": code}
        if key is not None:
            entry["key"] = key
        diagnostics.append(entry)

    for index, line in visible_lines(bodies, issue):
        number = index + 1
        if match := HEADING.match(line):
            level = len(match[1])
            title = heading_title(match)
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, title))
            sections.append({"heading": [name for _, name in headings], "line": number, "values": {}})
            continue
        if not (match := FIELD.match(line)):
            continue

        key = " ".join((match["inside"] or match["outside"] or match["plain"]).split())
        value = match["value"]
        normalized = f'{match["bullet"]}**{key}:** {value}'
        following = bodies[index + 1] if index + 1 < len(bodies) else ""
        multiline = following.strip() and not (HEADING.match(following) or LIST_ITEM.match(following))
        if not following.strip():
            next_block = index + 1
            while next_block < len(bodies) and not bodies[next_block].strip():
                next_block += 1
            multiline = next_block < len(bodies) and bodies[next_block].startswith(("  ", "\t"))
        if not value.strip():
            issue(number, "empty_value", key)
        if multiline:
            issue(number, "multiline_value", key)

        groups.setdefault((len(sections) - 1, key.casefold()), []).append((number, key, value, normalized))

    ambiguous = {entry["line"] for entry in diagnostics}
    for (section_index, _), records in groups.items():
        if len(records) != 1:
            for number, key, _, _ in records:
                issue(number, "duplicate_key", key)
            continue
        number, key, value, normalized = records[0]
        if number in ambiguous:
            continue
        sections[section_index]["values"][key] = value.rstrip(" \t")
        index = number - 1
        if bodies[index] != normalized:
            issue(number, "field_format", key)
            fixed[index] = normalized + lines[index][len(bodies[index]):]

    diagnostics.sort(key=lambda entry: (entry["line"], entry["code"]))
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    return {"sections": sections, "diagnostics": diagnostics}, bom + "".join(fixed)


def table_cells(line):
    parts = TABLE_SEPARATOR.split(line.strip(" \t"))
    if len(parts) == 1:
        return []
    cells = [parts[i] + parts[i + 1] for i in range(0, len(parts) - 1, 2)] + [parts[-1]]
    if cells[0] == "":
        cells = cells[1:]
    if cells and parts[-1] == "":
        cells.pop()
    return [cell.strip(" \t").replace(r"\|", "|") for cell in cells]


def starts_block(line):
    return bool(HEADING.match(line) or LIST_ITEM.match(line)
                or THEMATIC_BREAK.fullmatch(line) or line.startswith(">"))


def heading_title(match):
    return re.sub(r"(?:^|[ \t]+)#+[ \t]*$", "", match[2] or "").strip()


def read_table(lines, start):
    header = lines.get(start, "")
    columns = table_cells(header)
    if not columns or header.startswith((" ", "\t")) or starts_block(header):
        raise ValueError(f"line {start + 1}: expected a top-level pipe table header")
    alignment = table_cells(lines.get(start + 1, ""))
    if len(alignment) != len(columns) or not all(TABLE_ALIGNMENT.fullmatch(cell) for cell in alignment):
        raise ValueError(f"line {start + 2}: expected one table delimiter cell per column")
    if "" in columns or len(set(columns)) != len(columns):
        raise ValueError(f"line {start + 1}: table column names must be nonempty and unique")
    rows = []
    row = start + 2
    while (line := lines.get(row, "")).strip():
        stripped = line.lstrip(" ")
        if len(line) - len(stripped) <= 3 and starts_block(stripped):
            break
        cells = table_cells(line)
        if len(cells) != len(columns):
            raise ValueError(f"line {row + 1}: expected {len(columns)} pipe-delimited cells")
        rows.append((row + 1, cells))
        row += 1
    return columns, rows


def sum_table(lines, start, column):
    columns, rows = read_table(lines, start)
    if column not in columns:
        raise ValueError(f"line {start + 1}: unknown column {column!r}")
    column_index = columns.index(column)
    values = []
    for number, cells in rows:
        cell = cells[column_index]
        if not DECIMAL.fullmatch(cell):
            raise ValueError(f"line {number}: {column!r} requires a plain decimal, got {cell!r}")
        values.append(cell)

    # Allow the widest integer and fraction widths plus any carry from summing the rows.
    with localcontext() as context:
        context.prec = 2 * max(map(len, values), default=1) + len(str(len(values)))
        return format(sum(map(Decimal, values), Decimal(0)), "f")


def count_ordered_list(bodies, lines, start):
    first = ORDERED_ITEM.match(lines.get(start, ""))
    if not first:
        raise ValueError(f"line {start + 1}: expected the first item of a top-level ordered list")
    delimiter = first[2]
    count = 0
    content_indent = 0
    after_blank = False
    for index in range(start, len(bodies)):
        line = bodies[index].expandtabs(4)
        if not line.strip():
            after_blank = True
            continue
        content = line.lstrip(" ")
        indent = len(line) - len(content)
        if indent < content_indent or not count:
            if index not in lines:
                break
            if item := ORDERED_ITEM.match(content):
                if item[2] != delimiter:
                    break
                count += 1
                padding = item.end() - item.end(2)
                content_indent = indent + item.end(2) + (padding if 1 <= padding <= 4 else 1)
            elif after_blank or starts_block(content):
                break
        after_blank = False
    return count


def calculation_lines(text):
    bodies = [line.rstrip("\r\n") for line in source_lines(text)]

    def issue(line, code):
        raise ValueError(f"line {line}: {code.replace('_', ' ')}")

    return bodies, dict(visible_lines(bodies, issue))


def calculate(text, start, column=None):
    if start < 1:
        raise ValueError("line number must be positive")
    bodies, lines = calculation_lines(text)
    if column is None:
        return count_ordered_list(bodies, lines, start - 1)
    return sum_table(lines, start - 1, column)


def find_table(lines, name):
    title = None
    candidates = []
    for index, line in lines.items():
        if match := HEADING.match(line):
            title = heading_title(match)
        elif title == name and line and not line[0].isspace() and not starts_block(line):
            delimiter = table_cells(lines.get(index + 1, ""))
            if delimiter and table_cells(line) and all(TABLE_ALIGNMENT.fullmatch(cell) for cell in delimiter):
                candidates.append(index)
    if len(candidates) != 1:
        raise ValueError(f"expected one pipe table directly under heading {name!r}, found {len(candidates)}")
    return candidates[0]


def metric_expression(metric, columns):
    if metric == "count":
        return "count(*)", None, False
    operation, _, name = metric.partition(":")
    if name not in columns:
        raise ValueError(f"{metric!r}: expected count or an operation with an existing column")
    index = columns.index(name)
    identifier = f"c{index}"
    if operation == "distinct":
        return f"count(DISTINCT {identifier})", None, False
    if operation == "count":
        return f"count({identifier})", None, False
    if operation in ("sum", "min", "max"):
        return f"{operation}({identifier})", index, False
    value = f"CAST({identifier} AS DOUBLE)"
    if operation in ("avg", "median", "stddev"):
        function = "stddev_samp" if operation == "stddev" else operation
        return f"{function}({value})", index, True
    if re.fullmatch(r"p(?:100|[0-9]{1,2})", operation):
        percentile = Decimal(operation[1:]) / 100
        return f"quantile_cont({value}, {percentile})", index, True
    raise ValueError(f"unknown metric {operation!r}")


def decimal_type(rows, index, name, scale):
    widths = []
    for number, cells in rows:
        cell = cells[index]
        if not DECIMAL.fullmatch(cell):
            raise ValueError(f"line {number}: {name!r} requires a plain decimal, got {cell!r}")
        whole, _, fraction = cell.partition(".")
        widths.append((number, len(whole.lstrip("+-0")), len(fraction)))
    if scale is None:
        scale = max((fraction for _, _, fraction in widths), default=0)
    for number, whole, fraction in widths:
        if fraction > scale or whole + scale > 38:
            raise ValueError(f"line {number}: {name!r} does not fit DECIMAL(38, {scale}) exactly")
    return f"DECIMAL(38, {scale})"


def query_table(text, args, duckdb):
    _, lines = calculation_lines(text)
    start = find_table(lines, args.table)
    columns, rows = read_table(lines, start)
    labels = args.group_by + args.metric
    if len(set(labels)) != len(labels):
        raise ValueError("group columns and metric labels must be unique")
    metrics = [metric_expression(metric, columns) for metric in args.metric]
    if args.expect is not None and metrics[0][2] and args.tolerance is None:
        raise ValueError("this statistical metric requires --tolerance for an expectation")
    numeric = {index for _, index, _ in metrics if index is not None}
    scales = {}
    for item in args.decimal:
        name, _, scale = item.rpartition("=")
        if name not in columns or not re.fullmatch(r"[0-9]{1,2}", scale) or int(scale) > 38:
            raise ValueError(f"{item!r}: expected an existing column and a scale from 0 to 38")
        index = columns.index(name)
        if index in scales:
            raise ValueError(f"duplicate decimal scale for {name!r}")
        scales[index] = int(scale)
        numeric.add(index)
    for name in args.group_by:
        if name not in columns:
            raise ValueError(f"unknown group column {name!r}")

    groups = [f"c{columns.index(name)}" for name in args.group_by]
    expressions = groups + [expression for expression, _, _ in metrics]
    schema = [
        f"c{index} " + (decimal_type(rows, index, name, scales.get(index)) if index in numeric else "VARCHAR")
        for index, name in enumerate(columns)
    ]
    selection = f"SELECT {', '.join(expressions)} FROM markdown_rows"
    if groups:
        selection += f" GROUP BY {', '.join(groups)} ORDER BY " + ", ".join(f"{group} NULLS LAST" for group in groups)
    with duckdb.connect(":memory:", config={"threads": 1, "enable_external_access": False}) as connection:
        connection.execute(f"CREATE TABLE markdown_rows ({', '.join(schema)})")
        if rows:
            placeholders = ", ".join("?" for _ in columns)
            connection.executemany(
                f"INSERT INTO markdown_rows VALUES ({placeholders})",
                [[cell if cell else None for cell in cells] for _, cells in rows],
            )
        values = connection.execute(selection).fetchall()

    result = {"table": args.table, "header_line": start + 1, "rows": [dict(zip(labels, row)) for row in values]}
    if args.expect is not None:
        actual = values[0][0]
        if actual is None:
            raise ValueError("the metric is undefined for these rows")
        expected = Decimal(args.expect)
        actual_decimal = Decimal(str(actual))
        if args.tolerance is None:
            matches = actual_decimal == expected
        else:
            matches = abs(Fraction(actual_decimal) - Fraction(expected)) <= Fraction(args.tolerance)
        result.update(expected=args.expect, matches=matches)
    return result


def query_main():
    parser = argparse.ArgumentParser(prog=f"{Path(sys.argv[0]).name} query", description="Query one Markdown pipe table.")
    parser.add_argument("path", type=Path, help="UTF-8 Markdown document")
    parser.add_argument("--table", required=True, help="exact heading above the table")
    parser.add_argument("--group-by", action="append", default=[], metavar="COLUMN")
    parser.add_argument("--metric", action="append", required=True, metavar="OP[:COLUMN]",
                        help="count, distinct, sum, min, max, avg, median, stddev, or p0 to p100")
    parser.add_argument("--decimal", action="append", default=[], metavar="COLUMN=SCALE",
                        help="require values in a column to fit a fixed decimal scale")
    parser.add_argument("--expect", metavar="NUMBER", help="check one ungrouped metric")
    parser.add_argument("--tolerance", metavar="NUMBER", help="absolute tolerance for --expect")
    args = parser.parse_args(sys.argv[2:])
    if args.expect is not None and (not DECIMAL.fullmatch(args.expect) or args.group_by or len(args.metric) != 1):
        parser.error("--expect requires a plain number and exactly one ungrouped metric")
    if args.tolerance is not None and (
        args.expect is None or not DECIMAL.fullmatch(args.tolerance) or Decimal(args.tolerance) < 0
    ):
        parser.error("--tolerance requires --expect and a nonnegative plain decimal")
    try:
        import duckdb
    except ModuleNotFoundError:
        requirements = Path(__file__).with_name("requirements-analytics.txt")
        parser.error(f"query requires DuckDB. Install using python -m pip install -r {str(requirements)!r}")
    try:
        result = query_table(args.path.read_bytes().decode("utf-8"), args, duckdb)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, default=lambda value: format(value, "f")))
    except (OSError, ValueError, duckdb.Error) as error:
        parser.error(str(error))
    return int(not result.get("matches", True))


SEGMENT = " · "
SEGMENT_FIELD = re.compile(r"^(?P<key>[^\W\d][\w-]*)\s*:\s*(?P<value>.*)$")
SEGMENT_WORD = re.compile(r"^(?P<key>[^\W\d][\w-]*)\s+(?P<value>\S.*)$")
LOOSE_FIELD = re.compile(r"^(?P<key>[^\W\d][\w-]*):[ \t]+(?P<value>\S.*)$")
BULLET_ITEM = re.compile(r"^[-+*][ \t]+(?P<body>.*)$")
ID_TOKEN = re.compile(r"[\w.-]+")


def ticket_ids(text, patterns):
    """Every token of text that fully matches one of the compiled patterns, in order, without repeats."""
    found = []
    for token in ID_TOKEN.findall(text):
        token = token.strip(".")
        if token and token not in found and any(p.fullmatch(token) for p in patterns):
            found.append(token)
    return found


def tickets(text, patterns, path=""):
    """Index ticket lines and the many-to-many links between them.

    A ticket line is a heading or a top-level bullet whose first ` · ` segment holds an id matching a pattern:
    `- ENG-101 · req: R1, R2 · entry: ...` or `## Epic: ENG-100 · name`. Each later `key: value` segment (or
    `word ids` segment, such as `refines R1`) is a field; every id inside a field value is a link
    {from, field, to}. A `Key: ids` line directly under a ticket heading links from that heading's ticket.
    """
    patterns = [re.compile(p) if isinstance(p, str) else p for p in patterns]
    bodies = [line.rstrip("\r\n") for line in source_lines(text)]
    report = {"tickets": [], "links": [], "diagnostics": []}
    headings, heading_ticket, seen = [], None, {}

    def issue(line, code, key=None):
        entry = {"file": path, "line": line, "code": code}
        if key is not None:
            entry["key"] = key
        report["diagnostics"].append(entry)

    def link(source, key, value, number):
        for target in ticket_ids(value, patterns):
            report["links"].append({"from": source, "field": key, "to": target, "file": path, "line": number})

    for index, line in visible_lines(bodies, issue):
        number = index + 1
        heading = HEADING.match(line)
        bullet = None if heading else BULLET_ITEM.match(line)
        if heading:
            body = heading_title(heading)
            level = len(heading[1])
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, body))
            heading_ticket = None
        elif bullet:
            body = bullet["body"]
        else:
            loose = LOOSE_FIELD.match(line)
            if loose and heading_ticket:
                heading_ticket["fields"].setdefault(loose["key"], loose["value"].strip())
                link(heading_ticket["id"], loose["key"], loose["value"], number)
            continue
        segments = [s.strip() for s in body.split(SEGMENT)]
        head = segments[0]
        ids = ticket_ids(head, patterns)
        if not ids:
            continue
        ticket_id = ids[0]
        label = head[:head.find(ticket_id)].strip().rstrip(":").strip()
        parents = headings[:-1] if heading else headings
        ticket = {"id": ticket_id, "file": path, "line": number, "kind": "heading" if heading else "item",
                  "label": label, "heading": [name for _, name in parents], "fields": {}, "text": []}
        rest = head[head.find(ticket_id) + len(ticket_id):].strip()
        if rest:
            ticket["text"].append(rest)
        for segment in segments[1:]:
            field = SEGMENT_FIELD.match(segment)
            word = None if field else SEGMENT_WORD.match(segment)
            if word and not ticket_ids(word["value"], patterns):
                word = None
            match = field or word
            if not match:
                ticket["text"].append(segment)
                continue
            key, value = match["key"], match["value"].strip()
            if key in ticket["fields"]:
                issue(number, "duplicate_field", key)
                continue
            ticket["fields"][key] = value
            link(ticket_id, key, value, number)
        if ticket_id in seen:
            issue(number, "duplicate_ticket", ticket_id)
        else:
            seen[ticket_id] = number
        report["tickets"].append(ticket)
        if heading:
            heading_ticket = ticket
    return report


def tickets_tables(reports, duckdb):
    """Load ticket reports into DuckDB tables `tickets`, `fields` and `links` (the many-to-many edge table)."""
    connection = duckdb.connect(":memory:", config={"threads": 1, "enable_external_access": False})
    connection.execute("CREATE TABLE tickets (id VARCHAR, file VARCHAR, line INTEGER, kind VARCHAR, label VARCHAR, "
                       "heading VARCHAR, text VARCHAR)")
    connection.execute("CREATE TABLE fields (id VARCHAR, key VARCHAR, value VARCHAR, file VARCHAR, line INTEGER)")
    connection.execute("CREATE TABLE links (src VARCHAR, field VARCHAR, dst VARCHAR, file VARCHAR, line INTEGER)")
    for report in reports:
        rows = report["tickets"]
        if rows:
            connection.executemany("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?)", [
                [t["id"], t["file"], t["line"], t["kind"], t["label"], " / ".join(t["heading"]), SEGMENT.join(t["text"])]
                for t in rows])
        values = [[t["id"], k, v, t["file"], t["line"]] for t in rows for k, v in t["fields"].items()]
        if values:
            connection.executemany("INSERT INTO fields VALUES (?, ?, ?, ?, ?)", values)
        if report["links"]:
            connection.executemany("INSERT INTO links VALUES (?, ?, ?, ?, ?)", [
                [e["from"], e["field"], e["to"], e["file"], e["line"]] for e in report["links"]])
    return connection


def tickets_main():
    parser = argparse.ArgumentParser(
        prog=f"{Path(sys.argv[0]).name} tickets",
        description="Index ticket ids and their many-to-many links across Markdown documents.")
    parser.add_argument("paths", type=Path, nargs="+", help="UTF-8 Markdown documents")
    parser.add_argument("--pattern", action="append", required=True, metavar="REGEX",
                        help="a ticket id fully matches one; repeat for several conventions (ENG-123, R1, BUG-7)")
    parser.add_argument("--sql", metavar="QUERY",
                        help="DuckDB query over tables tickets, fields and links(src, field, dst); needs DuckDB")
    args = parser.parse_args(sys.argv[2:])
    try:
        patterns = [re.compile(p) for p in args.pattern]
    except re.error as error:
        parser.error(f"--pattern: {error}")
    reports = []
    for path in args.paths:
        try:
            reports.append(tickets(path.read_bytes().decode("utf-8"), patterns, str(path)))
        except (OSError, UnicodeError) as error:
            parser.exit(2, f"{error}\n")
    diagnostics = [d for r in reports for d in r["diagnostics"]]
    if args.sql is None:
        merged = {key: [item for r in reports for item in r[key]] for key in ("tickets", "links", "diagnostics")}
        print(json.dumps(merged, ensure_ascii=False, indent=2))
        return int(bool(diagnostics))
    try:
        import duckdb
    except ModuleNotFoundError:
        requirements = Path(__file__).with_name("requirements-analytics.txt")
        parser.error(f"--sql requires DuckDB. Install using python -m pip install -r {str(requirements)!r}")
    try:
        with tickets_tables(reports, duckdb) as connection:
            cursor = connection.execute(args.sql)
            names = [column[0] for column in cursor.description]
            rows = [dict(zip(names, row)) for row in cursor.fetchall()]
    except duckdb.Error as error:
        parser.error(str(error))
    print(json.dumps({"rows": rows, "diagnostics": diagnostics}, ensure_ascii=False, default=str))
    return int(bool(diagnostics))


def main():
    if sys.argv[1:2] == ["query"]:
        return query_main()
    if sys.argv[1:2] == ["tickets"]:
        return tickets_main()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="UTF-8 Markdown document")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fix", action="store_true", help="write normalized Markdown to stdout")
    mode.add_argument("--sum", nargs=2, metavar=("HEADER_LINE", "COLUMN"), help="sum a table column")
    mode.add_argument("--count-ol", type=int, metavar="FIRST_ITEM_LINE", help="count top-level ordered list items")
    parser.add_argument("--expect", metavar="NUMBER", help="fail if the calculation differs from this decimal")
    args = parser.parse_args()
    if args.expect is not None and (not DECIMAL.fullmatch(args.expect) or (args.sum is None and args.count_ol is None)):
        parser.error("--expect requires a plain number and a calculation")
    try:
        text = args.path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        parser.exit(2, f"{error}\n")

    if args.sum is not None or args.count_ol is not None:
        try:
            actual = calculate(text, int(args.sum[0]), args.sum[1]) if args.sum else calculate(text, args.count_ol)
        except ValueError as error:
            parser.error(str(error))
        result = {"actual": actual}
        if args.expect is not None:
            result.update(expected=args.expect, matches=Decimal(actual) == Decimal(args.expect))
        print(json.dumps(result))
        return int(not result.get("matches", True))

    report, fixed = audit(text)
    if args.fix:
        sys.stdout.buffer.write(fixed.encode("utf-8"))
        remaining = [entry for entry in report["diagnostics"] if entry["code"] != "field_format"]
        for entry in remaining:
            print(json.dumps(entry, ensure_ascii=False), file=sys.stderr)
        return int(bool(remaining))

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report["diagnostics"]))


if __name__ == "__main__":
    sys.exit(main())
