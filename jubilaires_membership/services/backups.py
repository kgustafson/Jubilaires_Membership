from __future__ import annotations

import os
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import BinaryIO


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = PROJECT_ROOT / "backups"
BACKUP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-(\d{3})\.dump$")

DB_CONTAINER = os.environ.get("JUBILAIRES_DB_CONTAINER", "jubilaires_membership_db")
DB_NAME = os.environ.get("JUBILAIRES_DB_NAME", "jubilaires_membership")
DB_USER = os.environ.get("JUBILAIRES_DB_USER", "admin")
DB_HOST = os.environ.get("JUBILAIRES_DB_HOST")
DB_PORT = os.environ.get("JUBILAIRES_DB_PORT", "5432")
DB_PASSWORD = os.environ.get("JUBILAIRES_DB_PASSWORD")


class DatabaseBackupError(RuntimeError):
    pass


def _backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def _command_error(result: subprocess.CompletedProcess[bytes]) -> str:
    message = result.stderr.decode("utf-8", errors="replace").strip()
    return message or f"Database command failed with exit code {result.returncode}."


def _metadata(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path": path,
        "size_bytes": stat.st_size,
        "size_label": _size_label(stat.st_size),
        "created_at": datetime.fromtimestamp(stat.st_mtime),
    }


def _size_label(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def list_backups() -> list[dict]:
    backups = [
        _metadata(path)
        for path in _backup_dir().iterdir()
        if path.is_file() and BACKUP_PATTERN.match(path.name)
    ]
    return sorted(backups, key=lambda item: item["created_at"], reverse=True)


def next_backup_path(today: date | None = None) -> Path:
    backup_date = today or date.today()
    prefix = backup_date.strftime("%Y-%m-%d")
    ordinals = []
    for path in _backup_dir().glob(f"{prefix}-*.dump"):
        match = BACKUP_PATTERN.match(path.name)
        if match:
            ordinals.append(int(match.group(1)))
    next_ordinal = max(ordinals, default=0) + 1
    return _backup_dir() / f"{prefix}-{next_ordinal:03d}.dump"


def create_backup() -> dict:
    backup_path = next_backup_path()
    result = subprocess.run(
        _backup_command(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=_database_command_env(),
    )
    if result.returncode != 0:
        raise DatabaseBackupError(_command_error(result))
    if not result.stdout:
        raise DatabaseBackupError("Database backup produced an empty file.")
    backup_path.write_bytes(result.stdout)
    return _metadata(backup_path)


def restore_backup(backup_name: str) -> None:
    backup_path = backup_path_for_name(backup_name)
    _restore_bytes(backup_path.read_bytes())


def restore_uploaded_backup(upload: BinaryIO) -> None:
    data = upload.read()
    if not data:
        raise DatabaseBackupError("Choose a backup file before restoring.")
    _restore_bytes(data)


def backup_path_for_name(backup_name: str) -> Path:
    safe_name = Path(backup_name).name
    if not BACKUP_PATTERN.match(safe_name):
        raise DatabaseBackupError("Choose a valid backup file.")
    backup_path = _backup_dir() / safe_name
    if not backup_path.exists():
        raise DatabaseBackupError("The selected backup file was not found.")
    return backup_path


def _restore_bytes(data: bytes) -> None:
    result = subprocess.run(
        _restore_command(),
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=_database_command_env(),
    )
    if result.returncode != 0:
        raise DatabaseBackupError(_command_error(result))


def _database_command_env() -> dict[str, str]:
    env = os.environ.copy()
    if DB_PASSWORD:
        env["PGPASSWORD"] = DB_PASSWORD
    return env


def _backup_command() -> list[str]:
    if DB_HOST:
        return [
            "pg_dump",
            "-h",
            DB_HOST,
            "-p",
            DB_PORT,
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-Fc",
        ]
    return ["docker", "exec", DB_CONTAINER, "pg_dump", "-U", DB_USER, "-d", DB_NAME, "-Fc"]


def _restore_command() -> list[str]:
    options = ["--clean", "--if-exists", "--no-owner", "--no-privileges"]
    if DB_HOST:
        return [
            "pg_restore",
            "-h",
            DB_HOST,
            "-p",
            DB_PORT,
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            *options,
        ]
    return ["docker", "exec", "-i", DB_CONTAINER, "pg_restore", "-U", DB_USER, "-d", DB_NAME, *options]
