#!/usr/bin/env python3
"""Extract usable roster photos from the membership DOCX into static/photos."""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path


DEFAULT_DOCX = Path("/Users/kurtgustafson/Downloads/ChapterMembership2026.docx")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHOTO_DIR = PROJECT_ROOT / "jubilaires_membership" / "static" / "photos"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def extract_photos(docx_path: Path, output_dir: Path = PHOTO_DIR) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(docx_path) as docx:
        media_names = sorted(
            name for name in docx.namelist()
            if name.startswith("word/media/")
            and Path(name).suffix.lower() in IMAGE_EXTENSIONS
        )
        for media_name in media_names:
            source_name = Path(media_name).name
            destination = output_dir / source_name
            with docx.open(media_name) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            count += 1
    return count


def main() -> int:
    docx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DOCX
    count = extract_photos(docx_path)
    print(f"Extracted {count} photos to {PHOTO_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
