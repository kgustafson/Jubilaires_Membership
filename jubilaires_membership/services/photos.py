from __future__ import annotations

import csv
import re
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps


APP_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = APP_ROOT / "static"
PHOTO_ROOT = STATIC_ROOT / "photos"
MANIFEST_PATH = PHOTO_ROOT / "manifest.csv"
ROSTER_PHOTO_DIR = PHOTO_ROOT / "roster"
PROFILE_PHOTO_DIR = PHOTO_ROOT / "profile"
PROFILE_SIZE = 512
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def safe_stem(value: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return stem or "photo"


def static_path(path: Path) -> str:
    return f"/static/{path.relative_to(STATIC_ROOT).as_posix()}"


def path_from_static_url(value: str) -> Path:
    static_prefix = "/static/"
    if not value.startswith(static_prefix):
        raise ValueError(f"Not a static path: {value}")
    return STATIC_ROOT / value.removeprefix(static_prefix)


def crop_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def normalize_profile_image(source: BinaryIO | bytes) -> Image.Image:
    payload = source if isinstance(source, bytes) else source.read()
    with Image.open(BytesIO(payload)) as image:
        image = ImageOps.exif_transpose(image)
        image = crop_square(image)
        image = image.resize((PROFILE_SIZE, PROFILE_SIZE), Image.Resampling.LANCZOS)
        if image.mode not in {"RGB", "L"}:
            background = Image.new("RGB", image.size, "white")
            if image.mode == "RGBA":
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image.convert("RGB"))
            image = background
        return image.convert("RGB")


def save_profile_upload(source: BinaryIO | bytes, folder: str, filename_stem: str) -> str:
    destination_dir = PROFILE_PHOTO_DIR / safe_stem(folder)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{safe_stem(filename_stem)}.jpg"
    image = normalize_profile_image(source)
    image.save(destination, format="JPEG", quality=86, optimize=True)
    return static_path(destination)


def image_dimensions(path: Path) -> tuple[int, int] | tuple[None, None]:
    try:
        with Image.open(path) as image:
            return image.width, image.height
    except OSError:
        return None, None


def photo_choices(assigned_paths: set[str] | None = None, current_path: str | None = None) -> list[dict[str, str | int | None]]:
    choices = []
    assigned_paths = assigned_paths or set()
    current_path = current_path or ""
    choice_paths = set()
    for row in roster_manifest_rows():
        try:
            choice_paths.add(path_from_static_url(row.get("static_path", "")))
        except ValueError:
            continue
    choice_paths.update(path for path in PROFILE_PHOTO_DIR.rglob("*") if path.is_file())
    for path in sorted(choice_paths):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        candidate_path = static_path(path)
        if candidate_path in assigned_paths and candidate_path != current_path:
            continue
        width, height = image_dimensions(path)
        choices.append(
            {
                "name": path.name,
                "path": candidate_path,
                "width": width,
                "height": height,
            }
        )
    return choices


def is_assignable(path: str, assigned_paths: set[str], current_path: str | None = None) -> bool:
    return bool(path) and (path not in assigned_paths or path == (current_path or ""))


def roster_manifest_rows() -> list[dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return []
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def unassigned_roster_photos(assigned_paths: set[str]) -> list[dict[str, str | int | None]]:
    photos = []
    for row in roster_manifest_rows():
        path = row.get("static_path", "")
        if not path or path in assigned_paths:
            continue
        try:
            source = path_from_static_url(path)
        except ValueError:
            continue
        if not source.exists() or source.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        width, height = image_dimensions(source)
        photos.append(
            {
                "position": row.get("position", ""),
                "path": path,
                "name": Path(path).name,
                "description": row.get("description", ""),
                "width": width,
                "height": height,
            }
        )
    return photos
