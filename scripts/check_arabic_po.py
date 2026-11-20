#!/usr/bin/env python3
"""Check Arabic gettext catalogs for untranslated entries and broken brace placeholders.

Usage: python scripts/check_arabic_po.py [path/to/ar.po]
The default target is erpnext/locale/ar.po. This read-only check intentionally does
not rewrite translations; fuzzy entries are excluded because they need human review.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from string import Formatter

FIELD = re.compile(r'^(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+("(?:\\.|[^"\\])*")\s*$')


def parse_po(path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    entry: dict[str, object] = {"flags": set(), "translations": {}}
    active: tuple[str, str | None] | None = None

    def finish() -> None:
        nonlocal entry, active
        if "msgid" in entry:
            entries.append(entry)
        entry = {"flags": set(), "translations": {}}
        active = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            finish()
            continue
        if line.startswith("#,"):
            entry["flags"].update(flag.strip() for flag in line[2:].split(","))
            continue
        if line.startswith("#"):
            continue

        match = FIELD.match(line)
        if match:
            field, literal = match.groups()
            value = ast.literal_eval(literal)
            if field.startswith("msgstr"):
                translations = entry["translations"]
                assert isinstance(translations, dict)
                translations[field] = value
                active = ("translation", field)
            else:
                entry[field] = value
                active = ("field", field)
            continue

        if line.startswith('"') and active:
            value = ast.literal_eval(line)
            kind, field = active
            if kind == "translation":
                translations = entry["translations"]
                assert isinstance(translations, dict) and field is not None
                translations[field] += value
            else:
                assert field is not None
                entry[field] = str(entry[field]) + value
            continue

        raise ValueError(f"{path}: unrecognized PO syntax: {raw_line}")

    finish()
    return entries


def placeholders(text: str) -> set[str]:
    found = set()
    for _, name, _, _ in Formatter().parse(text):
        if name:
            found.add(name.split(".", 1)[0].split("[", 1)[0])
    return found


def check_catalog(path: Path) -> list[str]:
    problems = []
    for entry in parse_po(path):
        msgid = str(entry.get("msgid", ""))
        if not msgid:
            continue  # gettext header
        flags = entry["flags"]
        translations = entry["translations"]
        assert isinstance(flags, set) and isinstance(translations, dict)
        if "fuzzy" in flags:
            continue

        values = list(translations.values())
        if not any(value.strip() for value in values):
            problems.append(f"Untranslated: {msgid[:100]!r}")
            continue

        if "python-brace-format" in flags:
            source = msgid + str(entry.get("msgid_plural", ""))
            expected = placeholders(source)
            for field, value in translations.items():
                if value.strip() and placeholders(value) != expected:
                    problems.append(
                        f"Placeholder mismatch ({field}) for {msgid[:100]!r}: "
                        f"expected {sorted(expected)}, found {sorted(placeholders(value))}"
                    )
    return problems


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("erpnext/locale/ar.po")
    problems = check_catalog(path)
    if problems:
        print("\n".join(problems))
        print(f"\nFound {len(problems)} issue(s) in {path}.")
        return 1
    print(f"No untranslated entries or brace-placeholder issues found in {path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
