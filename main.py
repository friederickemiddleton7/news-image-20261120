"""Entry point for the news-image-20261120 competition entry.

The picture itself is drawn ahead of time by make_image.py and stored next to
this file as entry.png. The grader only has to place it in the output
directory, so this program does exactly one thing: copy those bytes.

    python3 main.py                      -> /output/entry.png
    MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py

Standard library only, no network, no randomness: two runs produce identical
files.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

IMAGE_NAME = "entry.png"
MIN_BYTES = 4096                 # smaller than this is not a real picture
MAX_BYTES = 4 * 1024 * 1024      # generous ceiling; the entry is ~120 KB


def locate_source() -> Path:
    """entry.png always sits beside this script."""
    here = Path(__file__).resolve().parent
    return here / IMAGE_NAME


def locate_target_dir() -> Path:
    """MAKEFUN_OUTPUT_DIR wins; otherwise the grader's /output."""
    override = os.environ.get("MAKEFUN_OUTPUT_DIR", "").strip()
    return Path(override) if override else Path("/output")


def main() -> int:
    src = locate_source()
    if not src.is_file():
        print(f"error: {src} is missing; entry.png must sit beside main.py",
              file=sys.stderr)
        return 1

    size = src.stat().st_size
    if not MIN_BYTES <= size <= MAX_BYTES:
        print(f"error: {src} is {size} bytes, outside the expected "
              f"{MIN_BYTES}..{MAX_BYTES} range; rebuild it with make_image.py",
              file=sys.stderr)
        return 1

    dest_dir = locate_target_dir()
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create {dest_dir}: {exc}", file=sys.stderr)
        return 1

    dest = dest_dir / IMAGE_NAME
    try:
        shutil.copyfile(src, dest)
    except OSError as exc:
        print(f"error: cannot write {dest}: {exc}", file=sys.stderr)
        return 1

    written = dest.stat().st_size
    if written != size:
        print(f"error: {dest} is {written} bytes but the source is {size}",
              file=sys.stderr)
        return 1

    print(f"entry.png written to {dest} ({written} bytes, byte-identical)")
    return 0


if __name__ == "__main__":
    sys.exit(main())