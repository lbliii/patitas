#!/usr/bin/env python3
"""Extract Patitas from Bengal with import transformation.

This script copies patitas source files from Bengal and transforms
internal imports from `bengal.rendering.parsers.patitas.` to `patitas.`.

Usage:
    python scripts/extract_patitas.py [--verify] [--dry-run]

Options:
    --verify   Check for remaining Bengal imports after extraction
    --dry-run  Show what would be copied without copying
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

# Source and destination paths
BENGAL_ROOT = Path("/Users/llane/Documents/github/python/bengal")
PATITAS_ROOT = Path("/Users/llane/Documents/github/python/patitas")

BENGAL_PATITAS = BENGAL_ROOT / "bengal/rendering/parsers/patitas"
PATITAS_SRC = PATITAS_ROOT / "src/patitas"

# Import patterns to transform
IMPORT_PATTERNS = [
    # From imports
    (
        r"from bengal\.rendering\.parsers\.patitas\.",
        "from patitas.",
    ),
    # Absolute imports
    (
        r"import bengal\.rendering\.parsers\.patitas\.",
        "import patitas.",
    ),
]

# Files to skip (have Bengal-specific imports that need abstraction)
SKIP_FILES = {
    "wrapper.py",  # Bengal-specific adapter
    "__pycache__",
}

# Directories to skip entirely
SKIP_DIRS = {
    "__pycache__",
}

# Files with Bengal imports that need special handling (Phase 3+)
BENGAL_IMPORT_FILES = {
    "directives/builtins/admonition.py",
    "directives/builtins/button.py",
    "directives/builtins/cards.py",
    "directives/builtins/checklist.py",
    "directives/builtins/code_tabs.py",
    "directives/builtins/data_table.py",
    "directives/builtins/dropdown.py",
    "directives/builtins/embed.py",
    "directives/builtins/include.py",
    "directives/builtins/inline.py",
    "directives/builtins/media.py",
    "directives/builtins/misc.py",
    "directives/builtins/navigation.py",
    "directives/builtins/steps.py",
    "directives/builtins/tables.py",
    "directives/builtins/tabs.py",
    "directives/builtins/versioning.py",
    "directives/builtins/video.py",
    "parsing/blocks/directive.py",
    "renderers/html.py",
    "roles/builtins/icons.py",
    "wrapper.py",
}


def transform_imports(content: str) -> str:
    """Transform Bengal imports to patitas imports."""
    for pattern, replacement in IMPORT_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content


def has_remaining_bengal_imports(content: str) -> list[str]:
    """Check for any remaining Bengal imports."""
    lines = []
    for i, line in enumerate(content.split("\n"), 1):
        if "from bengal" in line or "import bengal" in line:
            # Skip comments
            if line.strip().startswith("#"):
                continue
            lines.append(f"  Line {i}: {line.strip()}")
    return lines


def copy_file(src: Path, dest: Path, *, dry_run: bool = False) -> tuple[bool, list[str]]:
    """Copy file with import transformation.

    Returns:
        (success, remaining_bengal_imports)
    """
    content = src.read_text()
    transformed = transform_imports(content)
    remaining = has_remaining_bengal_imports(transformed)

    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(transformed)

    return len(remaining) == 0, remaining


def extract_patitas(*, verify: bool = False, dry_run: bool = False) -> None:
    """Extract patitas files from Bengal."""
    print("=" * 60)
    print("Patitas Extraction Script")
    print("=" * 60)
    print()
    print(f"Source: {BENGAL_PATITAS}")
    print(f"Dest:   {PATITAS_SRC}")
    print()

    if dry_run:
        print("DRY RUN - no files will be copied")
        print()

    # Already extracted files (don't overwrite)
    already_extracted = {
        "location.py",
        "stringbuilder.py",
        "tokens.py",
        "protocols.py",
        "nodes.py",
        "__init__.py",
        "py.typed",
        "directives/__init__.py",
        "directives/options.py",
    }

    copied = []
    skipped = []
    has_bengal = []

    for src_path in sorted(BENGAL_PATITAS.rglob("*.py")):
        # Get relative path
        rel_path = src_path.relative_to(BENGAL_PATITAS)
        rel_str = str(rel_path)

        # Skip __pycache__
        if "__pycache__" in rel_str:
            continue

        # Skip already extracted
        if rel_str in already_extracted:
            print(f"  SKIP (already extracted): {rel_str}")
            skipped.append(rel_str)
            continue

        # Skip files with Bengal imports (handled in later phases)
        if rel_str in BENGAL_IMPORT_FILES:
            print(f"  SKIP (Bengal imports): {rel_str}")
            skipped.append(rel_str)
            continue

        # Skip wrapper.py
        if src_path.name in SKIP_FILES:
            print(f"  SKIP (explicit): {rel_str}")
            skipped.append(rel_str)
            continue

        dest_path = PATITAS_SRC / rel_path
        success, remaining = copy_file(src_path, dest_path, dry_run=dry_run)

        if success:
            print(f"  ✓ {rel_str}")
            copied.append(rel_str)
        else:
            print(f"  ⚠️ {rel_str} (has Bengal imports)")
            for line in remaining:
                print(f"    {line}")
            has_bengal.append((rel_str, remaining))

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Copied:  {len(copied)}")
    print(f"  Skipped: {len(skipped)}")
    print(f"  Bengal:  {len(has_bengal)}")

    if has_bengal and not dry_run:
        print()
        print("Files with remaining Bengal imports (need Phase 3+ work):")
        for file, lines in has_bengal:
            print(f"  {file}")
            for line in lines:
                print(f"    {line}")

    if verify:
        print()
        print("=" * 60)
        print("Verification")
        print("=" * 60)
        
        # Check all extracted files for Bengal imports
        all_clear = True
        for py_file in PATITAS_SRC.rglob("*.py"):
            rel = py_file.relative_to(PATITAS_SRC)
            content = py_file.read_text()
            remaining = has_remaining_bengal_imports(content)
            if remaining:
                print(f"  ✗ {rel}")
                for line in remaining:
                    print(f"    {line}")
                all_clear = False

        if all_clear:
            print("  ✓ No Bengal imports found in extracted files")
        else:
            print()
            print("ERROR: Some files still have Bengal imports")
            exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Patitas from Bengal")
    parser.add_argument("--verify", action="store_true", help="Verify no Bengal imports remain")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be copied")
    args = parser.parse_args()

    extract_patitas(verify=args.verify, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
