from __future__ import annotations

import csv
import re
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageChops, ImageOps


APP_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = APP_ROOT / "static"
PHOTO_ROOT = STATIC_ROOT / "photos"
MANIFEST_PATH = PHOTO_ROOT / "manifest.csv"
ROSTER_PHOTO_DIR = PHOTO_ROOT / "roster"
PROFILE_PHOTO_DIR = PHOTO_ROOT / "profile"
PROFILE_SIZE = 512
QUARTET_PHOTO_DIR = PHOTO_ROOT / "quartets"
QUARTET_SIZE = (2000, 1600)
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


def trim_uniform_border(image: Image.Image, threshold: int = 18) -> Image.Image:
    converted = image.convert("RGB")
    background = Image.new("RGB", converted.size, converted.getpixel((0, 0)))
    diff = ImageChops.difference(converted, background)
    mask = diff.convert("L").point(lambda value: 255 if value > threshold else 0)
    bbox = mask.getbbox()
    return converted.crop(bbox) if bbox else converted


def normalized_rotation(value: str | int | float | None) -> float:
    try:
        degrees = float(value or 0)
    except (TypeError, ValueError):
        return 0
    return degrees % 360


def rotate_image(image: Image.Image, clockwise_degrees: str | int | float | None, target_size: tuple[int, int] | None = None) -> Image.Image:
    degrees = normalized_rotation(clockwise_degrees)
    converted = image.convert("RGB")
    if degrees:
        converted = converted.rotate(-degrees, expand=True, fillcolor="white")
    if not target_size:
        return converted
    scale = max(target_size[0] / converted.width, target_size[1] / converted.height)
    resized_size = (max(1, round(converted.width * scale)), max(1, round(converted.height * scale)))
    converted = converted.resize(resized_size, Image.Resampling.LANCZOS)
    left = max(0, (converted.width - target_size[0]) // 2)
    top = max(0, (converted.height - target_size[1]) // 2)
    return converted.crop((left, top, left + target_size[0], top + target_size[1]))


def normalize_profile_image(source: BinaryIO | bytes, rotation_degrees: str | int | float | None = 0) -> Image.Image:
    payload = source if isinstance(source, bytes) else source.read()
    with Image.open(BytesIO(payload)) as image:
        image = ImageOps.exif_transpose(image)
        image = rotate_image(image, rotation_degrees)
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


def normalize_quartet_image(source: BinaryIO | bytes, rotation_degrees: str | int | float | None = 0) -> Image.Image:
    payload = source if isinstance(source, bytes) else source.read()
    with Image.open(BytesIO(payload)) as image:
        image = ImageOps.exif_transpose(image)
        image = rotate_image(image, rotation_degrees)
        image = trim_uniform_border(image)
        scale = max(QUARTET_SIZE[0] / image.width, QUARTET_SIZE[1] / image.height)
        resized_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        image = image.resize(resized_size, Image.Resampling.LANCZOS)
        converted = image.convert("RGB")
        left = max(0, (converted.width - QUARTET_SIZE[0]) // 2)
        top = max(0, (converted.height - QUARTET_SIZE[1]) // 2)
        return converted.crop((left, top, left + QUARTET_SIZE[0], top + QUARTET_SIZE[1]))


def save_profile_upload(source: BinaryIO | bytes, folder: str, filename_stem: str, rotation_degrees: str | int | float | None = 0) -> str:
    destination_dir = PROFILE_PHOTO_DIR / safe_stem(folder)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{safe_stem(filename_stem)}.jpg"
    image = normalize_profile_image(source, rotation_degrees)
    image.save(destination, format="JPEG", quality=86, optimize=True)
    return static_path(destination)


def save_quartet_upload(source: BinaryIO | bytes, filename_stem: str, rotation_degrees: str | int | float | None = 0) -> str:
    QUARTET_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    destination = QUARTET_PHOTO_DIR / f"{safe_stem(filename_stem)}.jpg"
    image = normalize_quartet_image(source, rotation_degrees)
    image.save(destination, format="JPEG", quality=88, optimize=True)
    return static_path(destination)


def rotate_static_photo(static_url: str, clockwise_degrees: str | int | float | None) -> tuple[int, int]:
    path = path_from_static_url(static_url)
    if not path.exists() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"Not a supported photo path: {static_url}")
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        target_size = image.size
        rotated = rotate_image(image, clockwise_degrees, target_size)
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        rotated.save(path, format="JPEG", quality=88, optimize=True)
    elif suffix == ".webp":
        rotated.save(path, format="WEBP", quality=88)
    elif suffix == ".gif":
        rotated.save(path, format="GIF")
    else:
        rotated.save(path, format="PNG", optimize=True)
    return rotated.size


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


def roster_photos(assignments: dict[str, dict] | None = None) -> list[dict[str, str | int | None]]:
    assignments = assignments or {}
    roster = []
    for row in roster_manifest_rows():
        path = row.get("static_path", "")
        try:
            source = path_from_static_url(path)
        except ValueError:
            continue
        if not source.exists() or source.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        width, height = image_dimensions(source)
        assignment = assignments.get(path)
        roster.append(
            {
                "position": row.get("position", ""),
                "path": path,
                "name": Path(path).name,
                "description": row.get("description", ""),
                "width": width,
                "height": height,
                "assignment": assignment,
                "is_assigned": bool(assignment),
            }
        )
    return roster
