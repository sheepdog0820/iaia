#!/usr/bin/env python3
"""Validate text integrity for the exact files staged in Git."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".htm",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".scss",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILENAMES = {".editorconfig", ".gitattributes", ".gitignore"}
UI_SUFFIXES = {".html", ".htm", ".js", ".jsx", ".mjs", ".ts", ".tsx"}
UI_PYTHON_NAMES = {
    "admin.py",
    "forms.py",
    "models.py",
    "serializers.py",
    "views.py",
}
MOJIBAKE_PATTERN = re.compile(
    r"(?:[\u7e3a\u7e67\u7e5d\u8b41\u873f\u879f\u8373\u83a0\u8708\u9015\u83f4\u9695].*){2}"
    r"|\u00c3.|\u00c2.|\u00e2\u20ac(?:\u2122|\u0153)?"
)


def run_git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or f"git {' '.join(args)} failed")
    return result.stdout


def repository_root() -> Path:
    output = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if output.returncode != 0:
        raise RuntimeError("Run this script inside a Git worktree.")
    return Path(output.stdout.decode("utf-8").strip())


def staged_paths(root: Path) -> list[Path]:
    output = run_git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [Path(item.decode("utf-8")) for item in output.split(b"\0") if item]


def staged_blob(root: Path, path: Path) -> bytes:
    return run_git(root, "show", f":{path.as_posix()}")


def index_blob_or_empty(root: Path, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f":{path}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", errors="replace")


def inspect_text(path: Path, data: bytes) -> list[str]:
    errors: list[str] = []
    if data.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{path}: UTF-8 BOM is not allowed")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [f"{path}: invalid UTF-8 ({exc})"]
    if "\r" in text:
        errors.append(f"{path}: CR or CRLF line endings detected; use LF")
    if "\ufffd" in text:
        errors.append(f"{path}: Unicode replacement character detected")
    for number, line in enumerate(text.splitlines(), start=1):
        if MOJIBAKE_PATTERN.search(line):
            errors.append(f"{path}:{number}: likely mojibake detected")
    return errors


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name.lower() in TEXT_FILENAMES


def is_ui_review_candidate(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in UI_SUFFIXES:
        return True
    if suffix == ".py" and path.name.lower() in UI_PYTHON_NAMES:
        return True
    return "templates" in {part.lower() for part in path.parts}


def policy_warnings(root: Path) -> list[str]:
    warnings: list[str] = []
    editorconfig = index_blob_or_empty(root, ".editorconfig").lower()
    attributes = index_blob_or_empty(root, ".gitattributes").lower()
    pyproject = index_blob_or_empty(root, "pyproject.toml").lower()

    if "charset = utf-8" not in editorconfig and "charset=utf-8" not in editorconfig:
        warnings.append(".editorconfig does not declare charset = utf-8")
    if "end_of_line = lf" not in editorconfig and "end_of_line=lf" not in editorconfig:
        warnings.append(".editorconfig does not declare end_of_line = lf")
    if "*.py text eol=lf" not in attributes:
        warnings.append(".gitattributes does not explicitly enforce LF for *.py")
    if "[tool.black]" not in pyproject:
        warnings.append("pyproject.toml does not configure Black")
    if "[tool.isort]" not in pyproject:
        warnings.append("pyproject.toml does not configure isort")
    return warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths",
        nargs="+",
        type=Path,
        help="Inspect working-tree paths instead of staged files (for script validation).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        root = repository_root()
        paths = args.paths if args.paths else staged_paths(root)
        if not paths:
            print("ERROR: no staged files to inspect", file=sys.stderr)
            return 1

        errors: list[str] = []
        ui_candidates: list[Path] = []
        validated_count = 0
        for path in paths:
            repo_path = path if not path.is_absolute() else path.relative_to(root)
            if not is_text_file(repo_path):
                continue
            validated_count += 1
            data = (root / repo_path).read_bytes() if args.paths else staged_blob(root, repo_path)
            errors.extend(inspect_text(repo_path, data))
            if is_ui_review_candidate(repo_path):
                ui_candidates.append(repo_path)

        for warning in policy_warnings(root):
            print(f"WARNING: {warning}")
        if ui_candidates:
            print("MANUAL UI LANGUAGE REVIEW REQUIRED:")
            for path in ui_candidates:
                print(f"  {path}")
            print("Confirm all changed user-visible literals are Japanese or an approved exception.")
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"OK: validated text integrity for {validated_count} text file(s)")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
