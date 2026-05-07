#!/usr/bin/env python3
"""Normalize extracted roster photos to 512x512 JPEG files."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from jubilaires_membership.services import photos


def source_path(static_path: str, media_file: str) -> Path:
    try:
        path = photos.path_from_static_url(static_path)
    except ValueError:
        path = photos.PHOTO_ROOT / media_file
    if path.exists():
        return path
    return photos.PHOTO_ROOT / media_file


def normalized_name(row: dict[str, str]) -> str:
    position = int(row["position"]) if row.get("position", "").isdigit() else 0
    stem = Path(row.get("media_file") or row.get("static_path") or f"image-{position}").stem
    return f"{position:03d}-{photos.safe_stem(stem)}.jpg"


def normalize_manifest() -> int:
    rows = photos.roster_manifest_rows()
    photos.ROSTER_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    updated_rows = []
    count = 0
    for row in rows:
        media_file = row.get("media_file", "")
        current_static_path = row.get("static_path", "")
        source = source_path(current_static_path, media_file)
        updated_row = dict(row)
        if source.exists() and source.suffix.lower() in photos.IMAGE_EXTENSIONS:
            destination = photos.ROSTER_PHOTO_DIR / normalized_name(row)
            image = photos.normalize_profile_image(source.read_bytes())
            image.save(destination, format="JPEG", quality=86, optimize=True)
            updated_row["original_static_path"] = current_static_path
            updated_row["static_path"] = photos.static_path(destination)
            count += 1
        updated_rows.append(updated_row)

    fieldnames = ["position", "relationship_id", "media_file", "static_path", "original_static_path", "description"]
    with photos.MANIFEST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    return count


def main() -> int:
    count = normalize_manifest()
    print(f"Normalized {count} roster photos to {photos.ROSTER_PHOTO_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
