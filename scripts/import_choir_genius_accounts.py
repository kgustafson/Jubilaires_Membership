#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jubilaires_membership.db import make_engine


SOURCE_SYSTEM = "Choir Genius"


def clean(value: object) -> str:
    return str(value or "").strip()


def parse_name(value: str) -> tuple[str, str]:
    if "," in value:
        last, first = value.split(",", 1)
        return clean(last), clean(first)
    parts = value.split()
    return clean(parts[-1]), clean(" ".join(parts[:-1]))


def parse_date(value: str) -> str | None:
    value = clean(value)
    if not value or value == "---" or value.lower() == "multiple times":
        return None
    for fmt in ("%m-%d-%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


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


def split_values(value: str) -> list[str]:
    return [part.strip() for part in clean(value).split(",") if part.strip()]


def raw_address(row: dict[str, str]) -> str | None:
    parts = [
        clean(row.get("Street")),
        clean(row.get("Additional")),
        clean(row.get("City")),
        clean(row.get("Province")),
        clean(row.get("Postal Code")),
        clean(row.get("Country")),
    ]
    return ", ".join(part for part in parts if part) or None


def load_aliases(path: Path) -> dict[str, str]:
    aliases: dict[str, str] = {}
    if not path.exists():
        return aliases
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if clean(row.get("status")).lower() == "confirmed":
                aliases[clean(row.get("source_name")).lower()] = clean(row.get("canonical_name"))
    return aliases


def ensure_status(connection, status: str) -> int:
    status_code = clean(status).lower() or "active"
    result = connection.execute(
        text(
            """
            INSERT INTO membership_status (status_code, description)
            VALUES (:status_code, :description)
            ON CONFLICT (status_code) DO UPDATE SET description = EXCLUDED.description
            RETURNING id
            """
        ),
        {"status_code": status_code, "description": f"{SOURCE_SYSTEM} status: {status}"},
    )
    return result.scalar_one()


def ensure_member(connection, last_name: str, first_name: str, status_id: int, source_path: str) -> tuple[int, bool]:
    existing = connection.execute(
        text(
            """
            SELECT id
            FROM member
            WHERE lower(last_name) = lower(:last_name)
              AND lower(first_name) = lower(:first_name)
            """
        ),
        {"last_name": last_name, "first_name": first_name},
    ).scalar()
    if existing:
        return int(existing), False

    member_id = connection.execute(
        text(
            """
            INSERT INTO member (last_name, first_name, status_id, source_document, notes)
            VALUES (:last_name, :first_name, :status_id, :source_document, :notes)
            RETURNING id
            """
        ),
        {
            "last_name": last_name,
            "first_name": first_name,
            "status_id": status_id,
            "source_document": source_path,
            "notes": f"Created from {SOURCE_SYSTEM} account export.",
        },
    ).scalar_one()
    return int(member_id), True


def replace_emails(connection, member_id: int, row: dict[str, str]) -> int:
    email_fields = [
        ("Primary email", "primary", True),
        ("Personal email", "personal", False),
        ("Work email", "work", False),
        ("Other email", "other", False),
    ]
    seen: set[str] = set()
    emails = []
    for field, label, is_primary in email_fields:
        email = clean(row.get(field))
        if not email or email.lower() in seen:
            continue
        seen.add(email.lower())
        emails.append((email, label, is_primary))
    if not emails:
        return 0

    connection.execute(text("DELETE FROM member_email WHERE member_id = :member_id"), {"member_id": member_id})
    for email, label, is_primary in emails:
        connection.execute(
            text(
                """
                INSERT INTO member_email (member_id, email_address, label, is_primary)
                VALUES (:member_id, :email_address, :label, :is_primary)
                """
            ),
            {"member_id": member_id, "email_address": email, "label": label, "is_primary": is_primary},
        )
    return len(emails)


def replace_phones(connection, member_id: int, row: dict[str, str]) -> int:
    phone_fields = [
        ("Mobile phone", "C", "mobile", True),
        ("Home phone", "H", "home", False),
        ("Work phone", "O", "work", False),
        ("Fax", "F", "fax", False),
    ]
    phones = []
    for field, phone_type, label, is_primary in phone_fields:
        phone = clean(row.get(field))
        if phone:
            phones.append((phone, phone_type, label, is_primary))
    if not phones:
        return 0

    connection.execute(text("DELETE FROM member_phone WHERE member_id = :member_id"), {"member_id": member_id})
    for phone, phone_type, label, is_primary in phones:
        connection.execute(
            text(
                """
                INSERT INTO member_phone (member_id, phone_type, phone_number, label, is_primary)
                VALUES (:member_id, :phone_type, :phone_number, :label, :is_primary)
                """
            ),
            {
                "member_id": member_id,
                "phone_type": phone_type,
                "phone_number": phone,
                "label": label,
                "is_primary": is_primary,
            },
        )
    return len(phones)


def replace_address(connection, member_id: int, row: dict[str, str]) -> int:
    if not any(clean(row.get(field)) for field in ("Street", "Additional", "City", "Province", "Postal Code", "Country")):
        return 0
    connection.execute(
        text("DELETE FROM member_address WHERE member_id = :member_id AND address_type = 'primary'"),
        {"member_id": member_id},
    )
    street = "\n".join(part for part in [clean(row.get("Street")), clean(row.get("Additional"))] if part) or None
    connection.execute(
        text(
            """
            INSERT INTO member_address (
                member_id, address_type, street, city, state, postal_code, country, raw_address, is_primary
            )
            VALUES (
                :member_id, 'primary', :street, :city, :state, :postal_code, :country, :raw_address, TRUE
            )
            """
        ),
        {
            "member_id": member_id,
            "street": street,
            "city": clean(row.get("City")) or None,
            "state": clean(row.get("Province")) or None,
            "postal_code": clean(row.get("Postal Code")) or None,
            "country": (clean(row.get("Country")) or "USA").upper(),
            "raw_address": raw_address(row),
        },
    )
    return 1


def replace_voice_part(connection, member_id: int, row: dict[str, str]) -> int:
    part = clean(row.get("Voice part"))
    if not part:
        return 0
    voice_part_id = connection.execute(
        text(
            """
            INSERT INTO voice_part (part_name)
            VALUES (:part_name)
            ON CONFLICT (part_name) DO UPDATE SET part_name = EXCLUDED.part_name
            RETURNING id
            """
        ),
        {"part_name": part},
    ).scalar_one()
    connection.execute(text("DELETE FROM member_voice_part WHERE member_id = :member_id"), {"member_id": member_id})
    connection.execute(
        text(
            """
            INSERT INTO member_voice_part (member_id, voice_part_id, is_primary)
            VALUES (:member_id, :voice_part_id, TRUE)
            ON CONFLICT (member_id, voice_part_id) DO UPDATE SET is_primary = TRUE
            """
        ),
        {"member_id": member_id, "voice_part_id": voice_part_id},
    )
    return 1


def replace_classifications(connection, member_id: int, row: dict[str, str]) -> int:
    connection.execute(
        text(
            """
            DELETE FROM member_classification_assignment mca
            USING member_classification mc
            WHERE mca.classification_id = mc.id
              AND mca.member_id = :member_id
              AND mc.source_system = :source_system
              AND mc.classification_type IN ('role', 'subgroup', 'label')
            """
        ),
        {"member_id": member_id, "source_system": SOURCE_SYSTEM},
    )
    count = 0
    for field, classification_type in (("Roles", "role"), ("Subgroups", "subgroup"), ("Labels", "label")):
        source_value = clean(row.get(field))
        for name in split_values(source_value):
            classification_id = connection.execute(
                text(
                    """
                    INSERT INTO member_classification (classification_type, name, source_system)
                    VALUES (:classification_type, :name, :source_system)
                    ON CONFLICT (classification_type, name, source_system)
                    DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """
                ),
                {"classification_type": classification_type, "name": name, "source_system": SOURCE_SYSTEM},
            ).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO member_classification_assignment (
                        member_id, classification_id, source_value, imported_at
                    )
                    VALUES (:member_id, :classification_id, :source_value, now())
                    ON CONFLICT (member_id, classification_id)
                    DO UPDATE SET source_value = EXCLUDED.source_value, imported_at = now()
                    """
                ),
                {"member_id": member_id, "classification_id": classification_id, "source_value": source_value},
            )
            count += 1
    return count


def replace_leadership_roles(connection, member_id: int, row: dict[str, str]) -> int:
    roles = split_values(clean(row.get("Leadership Role")))
    connection.execute(
        text("DELETE FROM member_role_assignment WHERE member_id = :member_id AND source_system = :source_system"),
        {"member_id": member_id, "source_system": SOURCE_SYSTEM},
    )
    for role in roles:
        role_id = connection.execute(
            text(
                """
                INSERT INTO member_role (role_name)
                VALUES (:role_name)
                ON CONFLICT (role_name) DO UPDATE SET role_name = EXCLUDED.role_name
                RETURNING id
                """
            ),
            {"role_name": role},
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO member_role_assignment (member_id, role_id, source_system)
                VALUES (:member_id, :role_id, :source_system)
                ON CONFLICT (member_id, role_id, source_system) DO UPDATE SET imported_at = now()
                """
            ),
            {"member_id": member_id, "role_id": role_id, "source_system": SOURCE_SYSTEM},
        )
    return len(roles)


def replace_emergency_contacts(connection, member_id: int, row: dict[str, str]) -> int:
    raw = clean(row.get("Emergency contacts"))
    connection.execute(
        text("DELETE FROM member_emergency_contact WHERE member_id = :member_id AND source_system = :source_system"),
        {"member_id": member_id, "source_system": SOURCE_SYSTEM},
    )
    if not raw:
        return 0
    phone_match = re.search(r"((?:\+?1[-. ]*)?(?:\(?\d{3}\)?[-. ]*)\d{3}[-. ]*\d{4})", raw)
    phone = phone_match.group(1) if phone_match else None
    before_phone = raw[: phone_match.start()].strip(" ,") if phone_match else raw
    parts = [part.strip() for part in before_phone.split(",") if part.strip()]
    name = parts[0] if parts else before_phone
    relationship = parts[1] if len(parts) > 1 else None
    connection.execute(
        text(
            """
            INSERT INTO member_emergency_contact (
                member_id, contact_name, relationship, phone_number, raw_contact, source_system
            )
            VALUES (:member_id, :contact_name, :relationship, :phone_number, :raw_contact, :source_system)
            """
        ),
        {
            "member_id": member_id,
            "contact_name": name or None,
            "relationship": relationship,
            "phone_number": phone,
            "raw_contact": raw,
            "source_system": SOURCE_SYSTEM,
        },
    )
    return 1


def upsert_spouse(connection, member_id: int, row: dict[str, str]) -> int:
    spouse = clean(row.get("Spouse Name"))
    if not spouse:
        return 0
    parts = spouse.split()
    first_name = parts[0]
    last_name = " ".join(parts[1:]) or None
    birth_date = parse_date(clean(row.get("Spouse Birthday")))
    existing = connection.execute(
        text(
            """
            SELECT id
            FROM member_family
            WHERE member_id = :member_id
              AND relationship = 'spouse'
              AND lower(first_name) = lower(:first_name)
            LIMIT 1
            """
        ),
        {"member_id": member_id, "first_name": first_name},
    ).scalar()
    if existing:
        family_member_id = existing
        connection.execute(
            text(
                """
                UPDATE member_family
                SET last_name = COALESCE(:last_name, last_name),
                    date_of_birth = COALESCE(:date_of_birth, date_of_birth),
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": existing, "last_name": last_name, "date_of_birth": birth_date},
        )
    else:
        family_member_id = connection.execute(
            text(
                """
                INSERT INTO member_family (member_id, first_name, last_name, relationship, date_of_birth, notes)
                VALUES (:member_id, :first_name, :last_name, 'spouse', :date_of_birth, :notes)
                RETURNING id
                """
            ),
            {
                "member_id": member_id,
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": birth_date,
                "notes": f"Imported from {SOURCE_SYSTEM} spouse field.",
            },
        ).scalar_one()
    upsert_important_date(
        connection,
        family_member_id=family_member_id,
        important_date=birth_date,
        title="Birthday",
        classification="birthday",
    )
    return 1


def upsert_external_account(connection, member_id: int, row: dict[str, str]) -> None:
    payload = json.dumps(row, sort_keys=True)
    connection.execute(
        text(
            """
            INSERT INTO member_external_account (
                member_id, source_system, username, qr_code, user_id, member_number,
                source_status, contact_pref, email_pref, company_name, url, parents,
                parent_emails, private_notes, skills, dues_paid_until, height_text,
                raw_payload, imported_at
            )
            VALUES (
                :member_id, :source_system, :username, :qr_code, :user_id, :member_number,
                :source_status, :contact_pref, :email_pref, :company_name, :url, :parents,
                :parent_emails, :private_notes, :skills, :dues_paid_until, :height_text,
                CAST(:raw_payload AS jsonb), now()
            )
            ON CONFLICT (member_id, source_system) DO UPDATE SET
                username = EXCLUDED.username,
                qr_code = EXCLUDED.qr_code,
                user_id = EXCLUDED.user_id,
                member_number = EXCLUDED.member_number,
                source_status = EXCLUDED.source_status,
                contact_pref = EXCLUDED.contact_pref,
                email_pref = EXCLUDED.email_pref,
                company_name = EXCLUDED.company_name,
                url = EXCLUDED.url,
                parents = EXCLUDED.parents,
                parent_emails = EXCLUDED.parent_emails,
                private_notes = EXCLUDED.private_notes,
                skills = EXCLUDED.skills,
                dues_paid_until = EXCLUDED.dues_paid_until,
                height_text = EXCLUDED.height_text,
                raw_payload = EXCLUDED.raw_payload,
                imported_at = now()
            """
        ),
        {
            "member_id": member_id,
            "source_system": SOURCE_SYSTEM,
            "username": clean(row.get("Username")) or None,
            "qr_code": clean(row.get("QR Code")) or None,
            "user_id": clean(row.get("User ID")) or None,
            "member_number": clean(row.get("Member ID")) or None,
            "source_status": clean(row.get("Status")) or None,
            "contact_pref": clean(row.get("Contact Pref")) or None,
            "email_pref": clean(row.get("Email Pref")) or None,
            "company_name": clean(row.get("Company Name")) or None,
            "url": clean(row.get("URL")) or None,
            "parents": clean(row.get("Parents")) or None,
            "parent_emails": clean(row.get("Parent emails")) or None,
            "private_notes": clean(row.get("Private notes")) or None,
            "skills": clean(row.get("Skills")) or None,
            "dues_paid_until": parse_date(clean(row.get("Dues Paid Until"))),
            "height_text": clean(row.get("Height")) or None,
            "raw_payload": payload,
        },
    )


def import_csv(path: Path) -> dict[str, int]:
    aliases = load_aliases(PROJECT_ROOT / "data_reconciliation" / "name_aliases.csv")
    engine = make_engine()
    summary = {
        "rows": 0,
        "matched_members": 0,
        "created_members": 0,
        "dates_updated": 0,
        "addresses_replaced": 0,
        "emails_replaced": 0,
        "phones_replaced": 0,
        "voice_parts_replaced": 0,
        "classifications": 0,
        "leadership_roles": 0,
        "emergency_contacts": 0,
        "spouses": 0,
    }
    with path.open(newline="", encoding="utf-8-sig") as handle, engine.begin() as connection:
        for row in csv.DictReader(handle):
            source_name = clean(row.get("Whole Name"))
            if not source_name:
                continue
            canonical_name = aliases.get(source_name.lower(), source_name)
            last_name, first_name = parse_name(canonical_name)
            status_id = ensure_status(connection, clean(row.get("Status")) or "Active")
            member_id, created = ensure_member(connection, last_name, first_name, status_id, str(path))
            summary["rows"] += 1
            summary["created_members" if created else "matched_members"] += 1

            membership_start_date = parse_date(clean(row.get("Member Since")))
            date_of_birth = parse_date(clean(row.get("Birthday")))
            anniversary_date = parse_date(clean(row.get("Anniversary")))
            connection.execute(
                text(
                    """
                    UPDATE member
                    SET status_id = :status_id,
                        membership_start_date = COALESCE(:membership_start_date, membership_start_date),
                        date_of_birth = COALESCE(:date_of_birth, date_of_birth),
                        anniversary_date = COALESCE(:anniversary_date, anniversary_date),
                        spouse_partner_name = COALESCE(:spouse_partner_name, spouse_partner_name),
                        source_document = :source_document,
                        updated_at = now()
                    WHERE id = :member_id
                    """
                ),
                {
                    "member_id": member_id,
                    "status_id": status_id,
                    "membership_start_date": membership_start_date,
                    "date_of_birth": date_of_birth,
                    "anniversary_date": anniversary_date,
                    "spouse_partner_name": clean(row.get("Spouse Name")) or None,
                    "source_document": str(path),
                },
            )
            if membership_start_date or date_of_birth or anniversary_date:
                summary["dates_updated"] += 1
            upsert_important_date(
                connection,
                member_id=member_id,
                important_date=membership_start_date,
                title="Membership Start",
                classification="membership_start",
            )
            upsert_important_date(
                connection,
                member_id=member_id,
                important_date=date_of_birth,
                title="Birthday",
                classification="birthday",
            )
            upsert_important_date(
                connection,
                member_id=member_id,
                important_date=anniversary_date,
                title="Anniversary",
                classification="anniversary",
            )

            summary["emails_replaced"] += replace_emails(connection, member_id, row)
            summary["phones_replaced"] += replace_phones(connection, member_id, row)
            summary["addresses_replaced"] += replace_address(connection, member_id, row)
            summary["voice_parts_replaced"] += replace_voice_part(connection, member_id, row)
            summary["classifications"] += replace_classifications(connection, member_id, row)
            summary["leadership_roles"] += replace_leadership_roles(connection, member_id, row)
            summary["emergency_contacts"] += replace_emergency_contacts(connection, member_id, row)
            summary["spouses"] += upsert_spouse(connection, member_id, row)
            upsert_external_account(connection, member_id, row)
    return summary


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: import_choir_genius_accounts.py /path/to/export.csv")
    summary = import_csv(Path(sys.argv[1]))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
