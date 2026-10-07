#!/usr/bin/env python3
"""Validate a full-corpus editing plan and render a lossless Markdown view.

Only Python's standard library is required. Run with --help for the three
commands. Editing offsets always refer to the unmodified CSV text field.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit


TEXT_ALIASES = (
    "视频文案（text）", "视频文案(text)", "视频文案", "正文", "文案",
    "text", "口播文案", "文案内容", "正文内容",
)
MECHANISMS = frozenset((
    "强制对话", "悬空", "预设", "矛盾", "发问", "预设价值", "价值承诺",
))
PLAN_KEYS = frozenset((
    "source_sha256", "text_column", "title_column", "likes_column", "records",
))
RECORD_KEYS = frozenset((
    "row", "edits", "opening", "delivery", "closing", "hooks",
))


class CorpusError(ValueError):
    """A source, plan, destination, or readback failed validation."""


def fail(message: str) -> None:
    raise CorpusError(message)


def exact_keys(value: Any, keys: frozenset[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{where}: expected an object")
    missing, extra = keys - value.keys(), value.keys() - keys
    if missing or extra:
        fail(f"{where}: missing keys {sorted(missing)}; unknown keys {sorted(extra)}")
    return value


def string(value: Any, where: str, *, nonempty: bool = False) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        fail(f"{where}: expected {'a nonempty' if nonempty else 'a'} string")
    if "\ufffd" in value or "\x00" in value:
        fail(f"{where}: damaged replacement or NUL character")
    # JSON permits escaped lone surrogates, which cannot be written as UTF-8.
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        fail(f"{where}: invalid Unicode surrogate")
    return value


def real_int(value: Any, where: str, *, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        fail(f"{where}: expected an integer >= {minimum}, not a boolean")
    return value


def read_csv(path: Path, text_column: str | None = None) -> dict[str, Any]:
    if path.suffix.lower() != ".csv":
        fail("input must have a .csv extension")
    raw = path.read_bytes()
    decoded = None
    encoding = ""
    for candidate in ("utf-8-sig", "gb18030"):
        try:
            decoded = raw.decode(candidate, errors="strict")
            encoding = candidate
            break
        except UnicodeDecodeError:
            continue
    if decoded is None:
        fail("CSV is neither strict UTF-8 nor strict GB18030")
    string(decoded, "CSV")
    try:
        csv.field_size_limit(sys.maxsize)
        reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
        columns = next(reader, None)
        if not columns:
            fail("CSV must contain a header row")
        if len(set(columns)) != len(columns):
            fail("CSV contains duplicate column names")
        if text_column is None:
            candidates = [column for column in columns if column in TEXT_ALIASES]
            if len(candidates) != 1:
                fail("specify --text-column: expected one exact text alias; "
                     f"found {candidates}")
            text_column = candidates[0]
        if text_column not in columns:
            fail(f"text column not found: {text_column!r}")
        records = []
        for row_number, values in enumerate(reader, 1):
            if len(values) != len(columns):
                fail(f"CSV record {row_number}: expected {len(columns)} fields, "
                     f"found {len(values)} (physical line {reader.line_num})")
            data = dict(zip(columns, values))
            records.append({"row": row_number, "data": data,
                            "text": data[text_column]})
    except csv.Error as exc:
        fail(f"malformed CSV: {exc}")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "encoding": encoding,
            "columns": columns, "text_column": text_column, "records": records}


def unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"plan JSON contains duplicate key: {key!r}")
        result[key] = value
    return result


def read_plan(path: Path) -> dict[str, Any]:
    raw = path.read_bytes().decode("utf-8-sig", errors="strict")
    string(raw, "plan JSON")
    try:
        plan = json.loads(raw, object_pairs_hook=unique_json_object,
                          parse_constant=lambda value: fail(
                              f"nonstandard JSON constant: {value}"))
    except json.JSONDecodeError as exc:
        fail(f"invalid plan JSON: {exc}")
    return exact_keys(plan, PLAN_KEYS, "plan")


def no_newlines(value: str) -> str:
    return value.replace("\r", "").replace("\n", "")


def beats(value: Any, where: str) -> list[str]:
    if not isinstance(value, list):
        fail(f"{where}: expected an array")
    for index, beat in enumerate(value):
        string(beat, f"{where}[{index}]", nonempty=True)
        if "\n" in beat or "\r" in beat:
            fail(f"{where}[{index}]: a beat must not contain CR or LF")
    return value


def apply_edits(source: str, edits: Any, where: str) -> str:
    if not isinstance(edits, list):
        fail(f"{where}: expected an array")
    checked = []
    for index, edit in enumerate(edits):
        label = f"{where}[{index}]"
        exact_keys(edit, frozenset(("start", "old", "new")), label)
        start = real_int(edit["start"], f"{label}.start", minimum=0)
        old = string(edit["old"], f"{label}.old", nonempty=True)
        new = string(edit["new"], f"{label}.new")
        if start + len(old) > len(source) or source[start:start + len(old)] != old:
            fail(f"{label}: old does not exactly match the original text at start")
        checked.append((start, old, new))
    checked.sort(key=lambda item: item[0])
    previous_end = 0
    for start, old, _ in checked:
        if start < previous_end:
            fail(f"{where}: edits overlap in the original text")
        previous_end = start + len(old)
    result = source
    for start, old, new in reversed(checked):
        result = result[:start] + new + result[start + len(old):]
    return result


def validate_plan(plan: dict[str, Any], source: dict[str, Any]) -> dict[int, Any]:
    digest = string(plan["source_sha256"], "source_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or digest != source["sha256"]:
        fail("source_sha256 does not match the exact CSV bytes")
    for key in ("text_column", "title_column", "likes_column"):
        column = plan[key]
        if column is None and key != "text_column":
            continue
        string(column, key)
        if column not in source["columns"]:
            fail(f"{key}: column not found: {column!r}")
        if key != "text_column" and column == plan["text_column"]:
            fail(f"{key}: must not reuse the text column")
    if plan["text_column"] != source["text_column"]:
        fail("text_column does not match the inspected source")
    if not isinstance(plan["records"], list):
        fail("records: expected an array")
    by_row = {}
    count = len(source["records"])
    for index, record in enumerate(plan["records"]):
        where = f"records[{index}]"
        exact_keys(record, RECORD_KEYS, where)
        row = real_int(record["row"], f"{where}.row", minimum=1)
        if row > count:
            fail(f"{where}.row: no such CSV record: {row}")
        if row in by_row:
            fail(f"duplicate source row in plan: {row}")
        opening = beats(record["opening"], f"{where}.opening")
        closing = beats(record["closing"], f"{where}.closing")
        if not isinstance(record["delivery"], list):
            fail(f"{where}.delivery: expected an array of nonempty beat arrays")
        delivery = []
        for paragraph_index, paragraph in enumerate(record["delivery"]):
            label = f"{where}.delivery[{paragraph_index}]"
            if not beats(paragraph, label):
                fail(f"{label}: a delivery paragraph must not be empty")
            delivery.append(paragraph)
        cleaned = apply_edits(source["records"][row - 1]["text"],
                              record["edits"], f"{where}.edits")
        flat = opening + [beat for paragraph in delivery for beat in paragraph] + closing
        if no_newlines("".join(flat)) != no_newlines(cleaned):
            fail(f"{where}: rejoined beats differ from the edited text "
                 "(only CR and LF may be ignored)")
        if not no_newlines(cleaned) and (opening or delivery or closing):
            fail(f"{where}: empty text requires all three regions to be empty")
        hooks = record["hooks"]
        if not isinstance(hooks, list):
            fail(f"{where}.hooks: expected an array")
        if hooks and not opening:
            fail(f"{where}.hooks: hooks require a nonempty opening")
        seen_hooks = set()
        for hook_index, hook in enumerate(hooks):
            label = f"{where}.hooks[{hook_index}]"
            exact_keys(hook, frozenset(("text", "mechanism")), label)
            fragment = string(hook["text"], f"{label}.text", nonempty=True)
            mechanism = string(hook["mechanism"], f"{label}.mechanism")
            if mechanism not in MECHANISMS:
                fail(f"{label}: mechanism is not in the seven-mechanism whitelist")
            if fragment not in opening[0]:
                fail(f"{label}: text must occur verbatim in the first opening beat")
            pair = (fragment, mechanism)
            if pair in seen_hooks:
                fail(f"{label}: duplicate text/mechanism pair")
            seen_hooks.add(pair)
        by_row[row] = record
    if set(by_row) != set(range(1, count + 1)):
        fail("plan must include every CSV record exactly once; "
             f"missing rows: {sorted(set(range(1, count + 1)) - set(by_row))}")
    return by_row


def likes_number(value: str) -> Decimal | None:
    candidate = value.strip().replace(",", "").replace("，", "")
    match = re.fullmatch(r"([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\s*([万亿kKmM]?)", candidate)
    if not match:
        return None
    exponent = {"": "0", "万": "4", "亿": "8",
                "k": "3", "m": "6"}[match.group(2).lower()]
    try:
        # Constructing a Decimal is exact even for values larger than the
        # active decimal arithmetic precision; no float/rounding is involved.
        return Decimal(match.group(1) + "e" + exponent)
    except InvalidOperation:
        return None


def escape_text(value: str) -> str:
    """Escape untrusted text while keeping only renderer-owned markup active."""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    escaped_lines = []
    for line in value.split("\n"):
        line = html.escape(line, quote=False)
        line = re.sub(r"([\\`*_{}\[\]()#+.!|~\-])", r"\\\1", line)
        line = line.replace("\t", "&#9;")
        # Leading spaces must not turn a literal beat into an indented code block.
        line = re.sub(r"^ +", lambda match: "&#32;" * len(match.group()), line)
        escaped_lines.append(line)
    return "<br>".join(escaped_lines)


def full_url(value: str) -> bool:
    if not re.fullmatch(r"https?://[^\s<>]+", value, flags=re.IGNORECASE):
        return False
    try:
        parsed = urlsplit(value)
        return bool(parsed.netloc and parsed.hostname)
    except ValueError:
        return False


def table_value(value: str) -> str:
    if full_url(value):
        # Character references keep a literal URL pipe from splitting a table;
        # decoding the href attribute gives the exact original field value.
        destination = html.escape(value, quote=True).replace("|", "&#124;")
        destination = destination.replace("\\", "&#92;")
        return f'<a href="{destination}">查看链接</a>'
    return escape_text(value)


def paragraph(lines: list[str]) -> str:
    return "  \n".join(escape_text(line) for line in lines)


def expected_markdown(input_path: Path, source: dict[str, Any],
                      plan: dict[str, Any], by_row: dict[int, Any]) -> str:
    records = list(source["records"])
    likes_column = plan["likes_column"]
    numbers = ({record["row"]: likes_number(record["data"][likes_column])
                for record in records} if likes_column is not None else {})
    if any(number is not None for number in numbers.values()):
        # Invalid/empty values follow all numeric values, including zero.
        records.sort(key=lambda record: (
            numbers[record["row"]] is None,
            (numbers[record["row"]].copy_negate()
             if numbers[record["row"]] is not None else Decimal(0)),
        ))
        sorting = f"按{escape_text(likes_column)}数值降序；同值保留源顺序，无效值置后。"
    else:
        sorting = "按源 CSV 记录顺序。"
    chunks = [f"# {escape_text(input_path.stem)}·断行整理版",
              f"来源：{escape_text(input_path.name)}；记录数：{len(records)}；排序：{sorting}"]
    for index, source_record in enumerate(records, 1):
        record = by_row[source_record["row"]]
        data = source_record["data"]
        title = data[plan["title_column"]] if plan["title_column"] is not None else ""
        title = title if title else f"记录 {source_record['row']}"
        chunks.append(f"## {index:03d}｜{escape_text(title)}")
        table = ["| 数据项 | 原值 |", "|---|---|"]
        for column in source["columns"]:
            if column != plan["text_column"]:
                table.append(f"| {escape_text(column)} | {table_value(data[column])} |")
        chunks.append("\n".join(table))
        if not (record["opening"] or record["delivery"] or record["closing"]):
            chunks.append("正文为空，未做断行。")
            continue
        if record["opening"]:
            chunks.extend(("### 开局", paragraph(record["opening"])))
            if record["hooks"]:
                hook_table = ["| 对应片段 | 截停机制 |", "|---|---|"]
                hook_table.extend(
                    f"| {escape_text(hook['text'])} | {escape_text(hook['mechanism'])} |"
                    for hook in record["hooks"]
                )
                chunks.append("\n".join(hook_table))
        if record["delivery"]:
            chunks.append("### 交付")
            chunks.extend(paragraph(group) for group in record["delivery"])
        if record["closing"]:
            chunks.extend(("### 收束", paragraph(record["closing"])))
    return "\n\n".join(chunks) + "\n"


def validate_destination(output: Path, source: Path, plan_path: Path) -> None:
    if output.suffix.lower() != ".md":
        fail("output must have a .md extension")
    for protected in (source, plan_path):
        if output.resolve() == protected.resolve():
            fail("output must not overwrite the source CSV or plan")
        if output.exists() and protected.exists() and os.path.samefile(output, protected):
            fail("output is a hard link to the source CSV or plan")
    if output.exists() and not output.is_file():
        fail("output exists and is not a regular file")


def atomic_write(output: Path, content: bytes, overwrite: bool) -> None:
    if not output.parent.is_dir():
        fail("output parent directory does not exist")
    if not overwrite and (output.exists() or output.is_symlink()):
        fail("output already exists; pass --overwrite to replace it")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{output.name}.", suffix=".tmp",
                                         dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temporary, output)
        else:
            # link() creates the completed file atomically and cannot clobber a
            # destination created after the existence check above.
            try:
                os.link(temporary, output)
            except FileExistsError:
                fail("output already exists; pass --overwrite to replace it")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser("inspect", help="inspect all CSV rows as JSON")
    inspect_parser.add_argument("input", type=Path)
    inspect_parser.add_argument("--text-column", help="exact source text column name")
    for name in ("render", "check"):
        command = commands.add_parser(name, help=("atomically render validated Markdown"
                                      if name == "render" else "compare existing Markdown byte for byte"))
        command.add_argument("input", type=Path)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--overwrite", action="store_true",
                             help="allow replacement when rendering; ignored by check")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "inspect":
            result = read_csv(args.input, args.text_column)
        else:
            plan = read_plan(args.plan)
            text_column = string(plan["text_column"], "text_column")
            source = read_csv(args.input, text_column)
            by_row = validate_plan(plan, source)
            validate_destination(args.output, args.input, args.plan)
            expected = expected_markdown(args.input, source, plan, by_row).encode("utf-8")
            if args.command == "check":
                if args.output.read_bytes() != expected:
                    fail("existing Markdown differs from the fully validated expected output")
            else:
                atomic_write(args.output, expected, args.overwrite)
                if args.output.read_bytes() != expected:
                    fail("written Markdown failed readback")
            result = {"status": "ok", "command": args.command,
                      "records": len(source["records"]), "output": str(args.output)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (CorpusError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
