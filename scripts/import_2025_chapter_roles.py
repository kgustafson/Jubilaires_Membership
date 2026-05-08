from __future__ import annotations

import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from jubilaires_membership import db

SOURCE_PATH = PROJECT_ROOT / "data_reconciliation" / "2025_chapter_roles.csv"
SOURCE_SYSTEM = "2025 Specified Chapter Roles"
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().replace(".", "").split())


def member_lookup() -> dict[str, dict]:
    rows = db.fetch_all(
        """
        SELECT id, first_name, last_name, preferred_name
        FROM member
        ORDER BY last_name, first_name
        """
    )
    lookup: dict[str, dict] = {}
    for row in rows:
        full_name = f"{row['first_name']} {row['last_name']}"
        lookup[normalize_name(full_name)] = row
        if row.get("preferred_name"):
            preferred = f"{row['preferred_name']} {row['last_name']}"
            lookup[normalize_name(preferred)] = row
    return lookup


def role_id(role_name: str) -> int:
    row = db.fetch_one_write(
        """
        INSERT INTO member_role (role_name)
        VALUES (:role_name)
        ON CONFLICT (role_name) DO UPDATE SET role_name = EXCLUDED.role_name
        RETURNING id
        """,
        {"role_name": role_name},
    )
    return row["id"]


def import_roles() -> None:
    lookup = member_lookup()
    missing: list[str] = []
    loaded = 0

    with SOURCE_PATH.open(newline="") as source_file:
        for row in csv.DictReader(source_file):
            role_name = row["role_name"].strip()
            member_name = row["member_name"].strip()
            notes = row.get("notes", "").strip() or None
            member = lookup.get(normalize_name(member_name))
            if not member:
                missing.append(member_name)
                continue
            db.execute(
                """
                INSERT INTO member_role_assignment (
                    member_id, role_id, start_date, end_date, source_system, notes
                )
                VALUES (
                    :member_id, :role_id, :start_date, :end_date, :source_system, :notes
                )
                ON CONFLICT (member_id, role_id, source_system) DO UPDATE SET
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    notes = EXCLUDED.notes,
                    imported_at = now()
                """,
                {
                    "member_id": member["id"],
                    "role_id": role_id(role_name),
                    "start_date": START_DATE,
                    "end_date": END_DATE,
                    "source_system": SOURCE_SYSTEM,
                    "notes": notes,
                },
            )
            loaded += 1

    if missing:
        names = ", ".join(sorted(set(missing)))
        raise SystemExit(f"Could not match these role names to members: {names}")
    print(f"Loaded {loaded} 2025 chapter role assignments from {SOURCE_PATH.name}.")


if __name__ == "__main__":
    import_roles()
