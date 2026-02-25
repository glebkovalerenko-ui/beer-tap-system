#!/usr/bin/env python3
"""Fail fast on suspicious encoding artifacts in changed repository text files."""

from __future__ import annotations

import argparse
import re
import subprocess
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

# Explicit required markers:
# - "\u0432\u0402", "\u0420\u2026", "\u0420\u00A4", "\u0420\u0452", "\u0420\u045F", "\u00D0", "\u00D1", "\uFFFD"
REQUIRED_MOJIBAKE_MARKERS = [
    "\u0432\u0402",  # РІР‚
    "\u0420\u2026",  # Р вЂ¦
    "\u0420\u00A4",  # Р В¤
    "\u0420\u0452",  # Р С’
    "\u0420\u045F",  # Р Сџ
    "\u00D0",  # Гђ
    "\u00D1",  # Г‘
    "\uFFFD",  # пїЅ
]

ADDITIONAL_MOJIBAKE_MARKERS = [
    "\u0420\u0098",
    "\u0420\u009E",
    "\u0420\u00B0",
    "\u0420\u00B5",
    "\u0420\u00BE",
    "\u0420\u00B8",
    "\u0420\u0404",
    "\u0420\u040E",
    "\u0420\u040B",
    "\u0420\u040F",
    "\u00C2",
    "\u00C3",
]

MOJIBAKE_MARKERS = list(dict.fromkeys(REQUIRED_MOJIBAKE_MARKERS + ADDITIONAL_MOJIBAKE_MARKERS))

R_LATIN_RE = re.compile(r"\u0420[A-Za-z]|[A-Za-z]\u0420")
R_OR_S_NON_CYRILLIC_RE = re.compile(
    r"[\u0420\u0421][\u0080-\u00BF\u00D0\u00D1\u00C2\u00C3\u2018\u2019\u201A\u201C\u201D\u2013\u2014]"
)

# Explicit bidi controls + direction marks commonly abused in trojan source.
BIDI_CONTROL_POINTS = set(range(0x202A, 0x202F))
BIDI_CONTROL_POINTS.update(range(0x2066, 0x206A))
BIDI_CONTROL_POINTS.update({0x200E, 0x200F, 0x061C})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check changed files (or all files) for UTF-8/mojibake/unicode-control issues."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="Scan all candidate text files in repository.")
    mode.add_argument("--staged", action="store_true", help="Scan staged files only (for pre-commit hooks).")
    mode.add_argument(
        "--diff-base",
        metavar="REF",
        help="Scan files changed in REF...HEAD (for CI pull_request checks).",
    )
    return parser.parse_args()


def run_git(root: Path, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def is_candidate_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS and not is_excluded(path)


def iter_candidate_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if not is_candidate_text_file(rel):
            continue
        yield rel


def _normalize_changed_paths(root: Path, file_list: list[str]) -> list[Path]:
    normalized: list[Path] = []
    seen: set[Path] = set()
    for item in file_list:
        rel = Path(item.strip())
        if not rel or rel.is_absolute():
            continue
        if rel in seen:
            continue
        path = root / rel
        if not path.is_file():
            continue
        if not is_candidate_text_file(rel):
            continue
        seen.add(rel)
        normalized.append(rel)
    return sorted(normalized)


def get_files_to_scan(root: Path, args: argparse.Namespace) -> list[Path]:
    if args.all:
        return sorted(iter_candidate_files(root))

    if args.staged:
        rc, stdout, stderr = run_git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
        if rc != 0:
            raise RuntimeError(f"git diff --cached failed: {stderr.strip()}")
        files = [line for line in stdout.splitlines() if line.strip()]
        return _normalize_changed_paths(root, files)

    if args.diff_base:
        rc, stdout, stderr = run_git(
            root,
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            f"{args.diff_base}...HEAD",
        )
        if rc != 0:
            raise RuntimeError(f"git diff {args.diff_base}...HEAD failed: {stderr.strip()}")
        files = [line for line in stdout.splitlines() if line.strip()]
        return _normalize_changed_paths(root, files)

    # Default local mode: scan files changed vs HEAD + untracked files.
    rc_diff, stdout_diff, stderr_diff = run_git(root, "diff", "--name-only", "--diff-filter=ACMR", "HEAD")
    if rc_diff != 0:
        raise RuntimeError(f"git diff HEAD failed: {stderr_diff.strip()}")
    rc_untracked, stdout_untracked, stderr_untracked = run_git(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
    )
    if rc_untracked != 0:
        raise RuntimeError(f"git ls-files --others failed: {stderr_untracked.strip()}")

    combined = [line for line in stdout_diff.splitlines() if line.strip()]
    combined.extend(line for line in stdout_untracked.splitlines() if line.strip())
    return _normalize_changed_paths(root, combined)


def collect_issues(root: Path, candidates: list[Path]) -> list[tuple[Path, int, int, str, str]]:
    issues: list[tuple[Path, int, int, str, str]] = []

    for rel in candidates:
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
                    issues.append((rel, line_no, match.start() + 1, "mojibake", "suspicious '\\u0420' next to Latin"))

                match = R_OR_S_NON_CYRILLIC_RE.search(line)
                if match:
                    issues.append((rel, line_no, match.start() + 1, "mojibake", "suspicious '\\u0420/\\u0421 + non-cyrillic'"))
            for col_no, ch in enumerate(line, start=1):
                code = ord(ch)
                if code in BIDI_CONTROL_POINTS:
                    issues.append((rel, line_no, col_no, "unicode-control", f"U+{code:04X}"))
                    continue

                category = unicodedata.category(ch)
                if category == "Cf" or (category == "Cc" and ch not in {"\t"}):
                    issues.append((rel, line_no, col_no, "unicode-control", f"U+{code:04X} ({category})"))

    return issues


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    args = parse_args()

    try:
        files_to_scan = get_files_to_scan(root, args)
    except RuntimeError as exc:
        print(f"[encoding_guard] ERROR: {exc}")
        return 2

    if not files_to_scan:
        print("[encoding_guard] OK: no candidate files to scan.")
        return 0

    print(f"[encoding_guard] Scanning {len(files_to_scan)} file(s).")
    issues = collect_issues(root, files_to_scan)

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



