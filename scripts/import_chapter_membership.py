#!/usr/bin/env python3
"""Import the ChapterMembership2026.docx roster into the Jubilaires database.

The source document is visually formatted, not a clean table. This importer uses
conservative heuristics and keeps the original block text on each member record
so questionable fields can be corrected in the web UI later.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine, text


DEFAULT_DOCX = Path("/Users/kurtgustafson/Downloads/ChapterMembership2026.docx")
DEFAULT_DATABASE_URL = "postgresql+psycopg2://admin:jubilaires@localhost:5433/jubilaires_membership"
ROSTER_PUBLICATION_YEAR = 2025

HEADER_WORDS = {
    "Names",
    "ames",
    "B'day",
    "Anniv",
    "Yrs",
    "Part",
    "Phones & Fax",
    "Address",
    "E-mail",
    "Quartets",
    "Status",
}

PART_ALIASES = {
    "tenor": ["Tenor"],
    "ten": ["Tenor"],
    "lead": ["Lead"],
    "bass": ["Bass"],
    "bari": ["Baritone"],
    "baritone": ["Baritone"],
    "ten/bari": ["Tenor", "Baritone"],
    "tenor/baritone": ["Tenor", "Baritone"],
    "baritone/tenor": ["Baritone", "Tenor"],
    "bari/ten": ["Baritone", "Tenor"],
    "violinist": ["Violinist"],
}

PHONE_RE = re.compile(r"(?:\(([HCOF])\)\s*)?(\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4})")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}\b")
PAGE_RE = re.compile(r"^-?\s*\d+\s*-?$")
NAME_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}


@dataclass
class ParsedMember:
    first_name: str
    last_name: str
    spouse_partner_name: str | None
    family_members: list[dict[str, str | None]]
    voice_parts: list[str]
    years_with_group: int | None
    status: str | None
    quartets: list[str]
    phones: list[tuple[str | None, str]]
    emails: list[tuple[str | None, str]]
    raw_address: str | None
    dates: list[str]
    raw_text: str


def docx_text(path: Path) -> str:
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def cleaned_lines(raw_text: str) -> list[str]:
    lines = []
    for line in raw_text.replace("\u00a0", " ").replace("\u2028", "\n").splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line or PAGE_RE.match(line):
            continue
        lines.append(line)
    return lines


def roster_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        starts_record = line.startswith("Names") or line.startswith("ames")
        if starts_record and current:
            blocks.append(current)
            current = []
        if starts_record or current:
            current.append(line)
    if current:
        blocks.append(current)
    return [block for block in blocks if any("," in line for line in block)]


def normalize_parts(block: list[str]) -> list[str]:
    header_text = " ".join(block[:8]).lower()
    parts = []
    for combined, values in (
        ("ten/bari", ["Tenor", "Baritone"]),
        ("tenor/baritone", ["Tenor", "Baritone"]),
        ("baritone/tenor", ["Baritone", "Tenor"]),
        ("bari/ten", ["Baritone", "Tenor"]),
    ):
        if combined in header_text:
            return values
    for key, value in PART_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", header_text):
            parts.extend(value)
    return list(dict.fromkeys(parts))


def years_with_group(block: list[str]) -> int | None:
    match = re.search(r"\b(\d+)\s*yrs?\b", " ".join(block[:8]).lower())
    return int(match.group(1)) if match else None


def text_between(block: list[str], start: str, end: str | None = None) -> list[str]:
    try:
        start_index = next(i for i, line in enumerate(block) if line == start or line.startswith(f"{start} "))
    except StopIteration:
        return []
    end_index = len(block)
    if end:
        for i in range(start_index + 1, len(block)):
            if block[i] == end or block[i].startswith(f"{end} "):
                end_index = i
                break
    return block[start_index + 1 : end_index]


def looks_like_address_line(line: str) -> bool:
    if line in HEADER_WORDS or line.startswith("Address") or line.startswith("E-mail"):
        return False
    if PHONE_RE.search(line) or EMAIL_RE.search(line):
        return False
    if line.startswith(("Quartets", "Status")):
        return False
    if re.match(r"^[A-Za-z]+:\s*(Same|Home)?$", line):
        return False
    if re.search(r"\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b", line):
        return True
    if re.search(r"\b[A-Z][a-z]+,\s*[A-Z]{2}\b", line):
        return True
    if re.match(r"^\d+\s+\S+", line):
        return True
    return False


def raw_address(block: list[str]) -> str | None:
    candidates = []
    candidates.extend(text_between(block, "Address", "E-mail"))
    candidates.extend(text_between(block, "E-mail", "Quartets"))
    address_lines = [line for line in candidates if looks_like_address_line(line)]
    return " ".join(dict.fromkeys(address_lines)).strip() or None


def first_name_line(block: list[str]) -> str | None:
    candidates = text_between(block, "Phones & Fax", "Address")
    if not candidates:
        candidates = block
    for line in candidates:
        if "," not in line or EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        cleaned = DATE_RE.sub("", line)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
        if cleaned and cleaned not in HEADER_WORDS:
            return cleaned
    return None


def parse_name(line: str) -> tuple[str, str, str | None] | None:
    if "," not in line:
        return None
    last_name, rest = [part.strip() for part in line.split(",", 1)]
    rest = DATE_RE.sub("", rest).strip()
    rest = re.sub(r"\s+", " ", rest)
    if not last_name or not rest:
        return None
    pieces = rest.split(" ")
    first_name = pieces[0]
    spouse_start = 2 if len(pieces) > 1 and pieces[1].lower() in NAME_SUFFIXES else 1
    spouse = " ".join(pieces[spouse_start:]).strip() or None
    return first_name, last_name, spouse


def parse_family_member(raw_name: str | None) -> dict[str, str | None] | None:
    if not raw_name:
        return None
    cleaned = re.sub(r"\s+", " ", raw_name).strip(" ,")
    if not cleaned or cleaned.lower() in {"same", "home"}:
        return None
    pieces = cleaned.split(" ", 1)
    return {
        "first_name": pieces[0],
        "last_name": pieces[1] if len(pieces) > 1 else None,
        "relationship": "spouse",
        "date_of_birth": None,
        "email_address": None,
        "picture_path": None,
        "notes": "Imported from spouse/family text in source roster.",
    }


def normalize_status(raw_status: str | None) -> str | None:
    if not raw_status:
        return None
    lowered = raw_status.lower()
    if "former" in lowered:
        return "former"
    if "inactive" in lowered or "inctive" in lowered:
        return "inactive"
    if "active" in lowered:
        return "active"
    return None


def is_status_line(line: str) -> bool:
    lowered = line.lower()
    return any(word in lowered for word in ("active", "inactive", "inctive", "former"))


def quartet_names(block: list[str]) -> list[str]:
    lines = [
        line for line in text_between(block, "Quartets", "Status")
        if line not in HEADER_WORDS and not EMAIL_RE.search(line) and not looks_like_address_line(line)
    ]
    if not lines:
        after_status = [
            line for line in text_between(block, "Status")
            if line not in HEADER_WORDS and not EMAIL_RE.search(line) and not looks_like_address_line(line)
        ]
        for line in after_status:
            if is_status_line(line):
                break
            lines.append(line)

    quartets = []
    for line in lines:
        quartets.extend(part.strip() for part in line.split(",") if part.strip())
    return quartets


def parse_block(block: list[str]) -> ParsedMember | None:
    name_line = first_name_line(block)
    if not name_line:
        return None
    parsed_name = parse_name(name_line)
    if not parsed_name:
        return None
    first_name, last_name, spouse = parsed_name

    full_text = "\n".join(block)
    phone_pairs = [(match.group(1), match.group(2).strip()) for match in PHONE_RE.finditer(full_text)]
    emails = [(None, email) for email in dict.fromkeys(EMAIL_RE.findall(full_text))]
    dates = DATE_RE.findall(full_text)

    status_lines = [line for line in text_between(block, "Status") if line not in HEADER_WORDS]
    raw_status = " ".join(status_lines[:2]).strip() or None
    status = normalize_status(raw_status)

    return ParsedMember(
        first_name=first_name,
        last_name=last_name,
        spouse_partner_name=spouse,
        family_members=[family] if (family := parse_family_member(spouse)) else [],
        voice_parts=normalize_parts(block),
        years_with_group=years_with_group(block),
        status=status,
        quartets=quartet_names(block),
        phones=phone_pairs,
        emails=emails,
        raw_address=raw_address(block),
        dates=dates,
        raw_text=full_text,
    )


def parsed_members(docx_path: Path) -> list[ParsedMember]:
    lines = cleaned_lines(docx_text(docx_path))
    return [member for block in roster_blocks(lines) if (member := parse_block(block))]


def scalar_id(connection, sql: str, params: dict) -> int:
    return int(connection.execute(text(sql), params).scalar_one())


def ensure_lookup(connection, table: str, column: str, value: str) -> int:
    return scalar_id(
        connection,
        f"""
        INSERT INTO {table} ({column})
        VALUES (:value)
        ON CONFLICT ({column}) DO UPDATE SET {column} = EXCLUDED.{column}
        RETURNING id
        """,
        {"value": value},
    )


def upsert_important_date(
    connection,
    *,
    classification: str,
    title: str,
    important_date: str | None,
    member_id: int | None = None,
    family_member_id: int | None = None,
) -> None:
    if not important_date:
        return
    if member_id is not None:
        connection.execute(
            text(
                """
                INSERT INTO important_date (member_id, important_date, title, classification)
                VALUES (:member_id, :important_date, :title, :classification)
                ON CONFLICT (member_id, classification) WHERE member_id IS NOT NULL
                DO UPDATE SET
                    important_date = EXCLUDED.important_date,
                    title = EXCLUDED.title,
                    updated_at = now()
                """
            ),
            {
                "member_id": member_id,
                "important_date": important_date,
                "title": title,
                "classification": classification,
            },
        )
    elif family_member_id is not None:
        connection.execute(
            text(
                """
                INSERT INTO important_date (family_member_id, important_date, title, classification)
                VALUES (:family_member_id, :important_date, :title, :classification)
                ON CONFLICT (family_member_id, classification) WHERE family_member_id IS NOT NULL
                DO UPDATE SET
                    important_date = EXCLUDED.important_date,
                    title = EXCLUDED.title,
                    updated_at = now()
                """
            ),
            {
                "family_member_id": family_member_id,
                "important_date": important_date,
                "title": title,
                "classification": classification,
            },
        )


def load_members(members: Iterable[ParsedMember], database_url: str, source_path: Path) -> int:
    engine = create_engine(database_url, pool_pre_ping=True)
    count = 0
    with engine.begin() as connection:
        source_id = scalar_id(
            connection,
            """
            INSERT INTO roster_source (source_name, source_path, notes)
            VALUES (:source_name, :source_path, :notes)
            RETURNING id
            """,
            {
                "source_name": source_path.name,
                "source_path": str(source_path),
                "notes": "Imported by scripts/import_chapter_membership.py",
            },
        )
        for member in members:
            part_ids = [
                ensure_lookup(connection, "voice_part", "part_name", voice_part)
                for voice_part in member.voice_parts
            ]
            primary_part_id = part_ids[0] if part_ids else None
            status_id = ensure_lookup(connection, "membership_status", "status_code", member.status) if member.status else None
            membership_start_date = f"{ROSTER_PUBLICATION_YEAR - member.years_with_group}-01-01" if member.years_with_group else None
            member_id = scalar_id(
                connection,
                """
                INSERT INTO member (
                    first_name, last_name, spouse_partner_name, voice_part_id, status_id,
                    membership_start_date, notes, source_document
                )
                VALUES (
                    :first_name, :last_name, :spouse_partner_name, :voice_part_id, :status_id,
                    :membership_start_date, :notes, :source_document
                )
                ON CONFLICT (last_name, first_name) DO UPDATE SET
                    spouse_partner_name = EXCLUDED.spouse_partner_name,
                    voice_part_id = EXCLUDED.voice_part_id,
                    status_id = EXCLUDED.status_id,
                    membership_start_date = EXCLUDED.membership_start_date,
                    notes = EXCLUDED.notes,
                    source_document = EXCLUDED.source_document,
                    updated_at = now()
                RETURNING id
                """,
                {
                    "first_name": member.first_name,
                    "last_name": member.last_name,
                    "spouse_partner_name": member.spouse_partner_name,
                    "voice_part_id": primary_part_id,
                    "status_id": status_id,
                    "membership_start_date": membership_start_date,
                    "notes": f"Roster source #{source_id}\nDates found: {', '.join(member.dates)}\n\n{member.raw_text}",
                    "source_document": str(source_path),
                },
            )
            upsert_important_date(
                connection,
                member_id=member_id,
                important_date=membership_start_date,
                title="Membership Start",
                classification="membership_start",
            )
            connection.execute(text("DELETE FROM member_voice_part WHERE member_id = :member_id"), {"member_id": member_id})
            for index, part_id in enumerate(part_ids):
                connection.execute(
                    text(
                        """
                        INSERT INTO member_voice_part (member_id, voice_part_id, is_primary)
                        VALUES (:member_id, :voice_part_id, :is_primary)
                        ON CONFLICT (member_id, voice_part_id) DO UPDATE SET
                            is_primary = EXCLUDED.is_primary
                        """
                    ),
                    {"member_id": member_id, "voice_part_id": part_id, "is_primary": index == 0},
                )
            connection.execute(text("DELETE FROM member_phone WHERE member_id = :member_id"), {"member_id": member_id})
            connection.execute(text("DELETE FROM member_email WHERE member_id = :member_id"), {"member_id": member_id})
            connection.execute(
                text(
                    """
                    DELETE FROM member_family
                    WHERE member_id = :member_id
                      AND notes = 'Imported from spouse/family text in source roster.'
                    """
                ),
                {"member_id": member_id},
            )
            connection.execute(text("DELETE FROM member_address WHERE member_id = :member_id"), {"member_id": member_id})
            connection.execute(text("DELETE FROM member_quartet WHERE member_id = :member_id"), {"member_id": member_id})

            for index, (phone_type, phone_number) in enumerate(dict.fromkeys(member.phones)):
                connection.execute(
                    text(
                        """
                        INSERT INTO member_phone (member_id, phone_type, phone_number, is_primary)
                        VALUES (:member_id, :phone_type, :phone_number, :is_primary)
                        """
                    ),
                    {
                        "member_id": member_id,
                        "phone_type": phone_type,
                        "phone_number": phone_number,
                        "is_primary": index == 0,
                    },
                )

            for index, (label, email_address) in enumerate(dict.fromkeys(member.emails)):
                connection.execute(
                    text(
                        """
                        INSERT INTO member_email (member_id, label, email_address, is_primary)
                        VALUES (:member_id, :label, :email_address, :is_primary)
                        """
                    ),
                    {
                        "member_id": member_id,
                        "label": label,
                        "email_address": email_address,
                        "is_primary": index == 0,
                    },
                )

            for family_member in member.family_members:
                family_member_id = connection.execute(
                    text(
                        """
                        INSERT INTO member_family (
                            member_id, first_name, last_name, relationship,
                            date_of_birth, email_address, picture_path, notes
                        )
                        VALUES (
                            :member_id, :first_name, :last_name, :relationship,
                            :date_of_birth, :email_address, :picture_path, :notes
                        )
                        RETURNING id
                        """
                    ),
                    {"member_id": member_id, **family_member},
                ).scalar_one()
                upsert_important_date(
                    connection,
                    family_member_id=family_member_id,
                    important_date=family_member.get("date_of_birth"),
                    title="Birthday",
                    classification="birthday",
                )

            if member.raw_address:
                connection.execute(
                    text(
                        """
                        INSERT INTO member_address (member_id, raw_address, is_primary)
                        VALUES (:member_id, :raw_address, true)
                        """
                    ),
                    {"member_id": member_id, "raw_address": member.raw_address},
                )

            for quartet_name in dict.fromkeys(member.quartets):
                quartet_id = ensure_lookup(connection, "quartet", "name", quartet_name)
                connection.execute(
                    text(
                        """
                        INSERT INTO member_quartet (member_id, quartet_id, membership_state)
                        VALUES (:member_id, :quartet_id, 'primary')
                        ON CONFLICT (member_id, quartet_id) DO UPDATE SET
                            membership_state = EXCLUDED.membership_state
                        """
                    ),
                    {"member_id": member_id, "quartet_id": quartet_id},
                )
            count += 1
    return count


def main() -> int:
    docx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DOCX
    database_url = os.environ.get("JUBILAIRES_DATABASE_URL", DEFAULT_DATABASE_URL)
    members = parsed_members(docx_path)
    loaded = load_members(members, database_url, docx_path)
    print(f"Loaded {loaded} members from {docx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
