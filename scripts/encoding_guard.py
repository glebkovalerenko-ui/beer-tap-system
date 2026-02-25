#!/usr/bin/env python3
"""Fail fast on suspicious encoding artifacts in repository text files."""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".svelte",
    ".rs",
    ".md",
    ".yml",
    ".yaml",
    ".toml",
    ".json",
    ".ini",
    ".sh",
    ".txt",
}

EXCLUDED_DIRS = {
    "node_modules",
    "dist",
    "target",
    ".git",
    "__pycache__",
    ".pytest_cache",
}

MOJIBAKE_MARKERS = [
    "\u0432\u0402",
    "\u0420\u045f",
    "\u0420\u0452",
    "\u0420\u00A4",
    "\u0420\u0098",
    "\u0420\u009E",
    "\u0420\u00B0",
    "\u0420\u00B5",
    "\u0420\u00BE",
    "\u0420\u00B8",
    "\u0420\u0404",
    "\u0420\u040e",
    "\u0420\u040b",
    "\u0420\u040f",
    "\u00d0",
    "\u00d1",
    "\u00c3",
    "\u00c2",
    "\ufffd",
]

R_LATIN_RE = re.compile(r"\u0420[A-Za-z]|[A-Za-z]\u0420")
R_OR_S_NON_CYRILLIC_RE = re.compile(
    r"[\u0420\u0421][\u0080-\u00BF\u00D0\u00D1\u00C2\u00C3\u2018\u2019\u201A\u201C\u201D\u2013\u2014]"
)

# Explicit bidi controls + direction marks commonly abused in trojan source.
BIDI_CONTROL_POINTS = set(range(0x202A, 0x202F))
BIDI_CONTROL_POINTS.update(range(0x2066, 0x206A))
BIDI_CONTROL_POINTS.update({0x200E, 0x200F, 0x061C})


def is_excluded(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return True
    return False


def iter_candidate_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        rel = path.relative_to(root)
        if is_excluded(rel):
            continue
        yield rel


def collect_issues(root: Path) -> list[tuple[Path, int, int, str, str]]:
    issues: list[tuple[Path, int, int, str, str]] = []

    for rel in iter_candidate_files(root):
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            issues.append((rel, 1, 1, "encoding", f"invalid UTF-8: {exc}"))
            continue

        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if rel != Path("scripts/encoding_guard.py"):
                for marker in MOJIBAKE_MARKERS:
                    idx = line.find(marker)
                    if idx != -1:
                        codepoints = " ".join(f"U+{ord(ch):04X}" for ch in marker)
                        issues.append((rel, line_no, idx + 1, "mojibake", f"marker {codepoints}"))

                match = R_LATIN_RE.search(line)
                if match:
                    issues.append((rel, line_no, match.start() + 1, "mojibake", "suspicious 'Р' next to Latin"))

                match = R_OR_S_NON_CYRILLIC_RE.search(line)
                if match:
                    issues.append((rel, line_no, match.start() + 1, "mojibake", "suspicious 'Р/С + non-cyrillic' sequence"))

            for col_no, ch in enumerate(line, start=1):
                code = ord(ch)
                if unicodedata.category(ch) == "Cf" or code in BIDI_CONTROL_POINTS:
                    issues.append((rel, line_no, col_no, "unicode-control", f"U+{code:04X}"))

    return issues


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    issues = collect_issues(root)

    if issues:
        print("[encoding_guard] Found encoding issues:")
        for rel, line_no, col_no, kind, detail in issues:
            safe_detail = detail.encode("unicode_escape").decode("ascii")
            print(f"{rel}:{line_no}:{col_no}: {kind}: {safe_detail}")
        return 1

    print("[encoding_guard] OK: no UTF-8/mojibake/bidi-control issues found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
