from __future__ import annotations

from typing import Optional

from jubilaires_membership import db


FAMILY_RELATIONSHIPS = [
    "spouse",
    "partner",
    "son",
    "daughter",
    "brother",
    "sister",
    "father",
    "mother",
    "child",
    "parent",
    "family",
    "other",
]


def optional_date(value: str) -> str | None:
    return value.strip() or None


def optional_int(value: str) -> int | None:
    return int(value) if value.strip() else None


def dashboard_counts() -> dict:
    counts = db.fetch_one(
        """
        SELECT
            COUNT(DISTINCT m.id) AS total_members,
            COUNT(DISTINCT m.id) FILTER (WHERE lower(ms.status_code) = 'active') AS active_members,
            COUNT(DISTINCT m.id) FILTER (WHERE vp.part_name = 'Tenor') AS tenors,
            COUNT(DISTINCT m.id) FILTER (WHERE vp.part_name = 'Lead') AS leads,
            COUNT(DISTINCT m.id) FILTER (WHERE vp.part_name = 'Baritone') AS baritones,
            COUNT(DISTINCT m.id) FILTER (WHERE vp.part_name = 'Bass') AS basses
        FROM member m
        LEFT JOIN membership_status ms ON ms.id = m.status_id
        LEFT JOIN member_voice_part mvp ON mvp.member_id = m.id
        LEFT JOIN voice_part vp ON vp.id = mvp.voice_part_id
        """
    )
    return counts or {}


def member_rows(status: Optional[str] = None, part: Optional[str] = None, search: Optional[str] = None) -> list[dict]:
    filters = []
    params = {}
    if status:
        filters.append("lower(ms.status_code) = lower(:status)")
        params["status"] = status
    if part:
        filters.append(
            """
            EXISTS (
                SELECT 1
                FROM member_voice_part filter_mvp
                JOIN voice_part filter_vp ON filter_vp.id = filter_mvp.voice_part_id
                WHERE filter_mvp.member_id = m.id
                  AND filter_vp.part_name = :part
            )
            """
        )
        params["part"] = part
    if search:
        filters.append(
            """
            (
                m.first_name ILIKE :search
                OR m.last_name ILIKE :search
                OR EXISTS (
                    SELECT 1
                    FROM member_family mf
                    WHERE mf.member_id = m.id
                      AND (mf.first_name ILIKE :search OR mf.last_name ILIKE :search)
                )
            )
            """
        )
        params["search"] = f"%{search}%"

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    return db.fetch_all(
        f"""
        SELECT
            m.id,
            m.last_name,
            m.first_name,
            family_summary.family_names,
            m.membership_start_date,
            part_summary.part_names,
            ms.status_code,
            primary_phone.phone_number AS primary_phone,
            primary_email.email_address AS primary_email
        FROM member m
        LEFT JOIN membership_status ms ON ms.id = m.status_id
        LEFT JOIN LATERAL (
            SELECT string_agg(vp.part_name, ', ' ORDER BY mvp.is_primary DESC, vp.part_name) AS part_names
            FROM member_voice_part mvp
            JOIN voice_part vp ON vp.id = mvp.voice_part_id
            WHERE mvp.member_id = m.id
        ) part_summary ON true
        LEFT JOIN LATERAL (
            SELECT phone_number
            FROM member_phone
            WHERE member_id = m.id
            ORDER BY is_primary DESC, id
            LIMIT 1
        ) primary_phone ON true
        LEFT JOIN LATERAL (
            SELECT email_address
            FROM member_email
            WHERE member_id = m.id
            ORDER BY is_primary DESC, id
            LIMIT 1
        ) primary_email ON true
        LEFT JOIN LATERAL (
            SELECT string_agg(
                trim(concat_ws(' ', first_name, last_name)) || ' (' || relationship || ')',
                ', ' ORDER BY id
            ) AS family_names
            FROM member_family
            WHERE member_id = m.id
        ) family_summary ON true
        {where}
        ORDER BY m.last_name, m.first_name
        """,
        params,
    )


def member_detail(member_id: int) -> Optional[dict]:
    member = db.fetch_one(
        """
        SELECT m.*, part_summary.part_names, ms.status_code
        FROM member m
        LEFT JOIN membership_status ms ON ms.id = m.status_id
        LEFT JOIN LATERAL (
            SELECT string_agg(vp.part_name, ', ' ORDER BY mvp.is_primary DESC, vp.part_name) AS part_names
            FROM member_voice_part mvp
            JOIN voice_part vp ON vp.id = mvp.voice_part_id
            WHERE mvp.member_id = m.id
        ) part_summary ON true
        WHERE m.id = :member_id
        """,
        {"member_id": member_id},
    )
    if not member:
        return None

    member["phones"] = db.fetch_all(
        "SELECT * FROM member_phone WHERE member_id = :member_id ORDER BY is_primary DESC, id",
        {"member_id": member_id},
    )
    member["voice_parts"] = db.fetch_all(
        """
        SELECT vp.*, mvp.is_primary, mvp.notes
        FROM member_voice_part mvp
        JOIN voice_part vp ON vp.id = mvp.voice_part_id
        WHERE mvp.member_id = :member_id
        ORDER BY mvp.is_primary DESC, vp.part_name
        """,
        {"member_id": member_id},
    )
    member["emails"] = db.fetch_all(
        "SELECT * FROM member_email WHERE member_id = :member_id ORDER BY is_primary DESC, id",
        {"member_id": member_id},
    )
    member["family"] = db.fetch_all(
        """
        SELECT *
        FROM member_family
        WHERE member_id = :member_id
        ORDER BY
            CASE relationship
                WHEN 'spouse' THEN 1
                WHEN 'partner' THEN 2
                WHEN 'son' THEN 3
                WHEN 'daughter' THEN 4
                ELSE 10
            END,
            first_name,
            last_name
        """,
        {"member_id": member_id},
    )
    member["addresses"] = db.fetch_all(
        "SELECT * FROM member_address WHERE member_id = :member_id ORDER BY is_primary DESC, id",
        {"member_id": member_id},
    )
    member["quartets"] = db.fetch_all(
        """
        SELECT q.name, mq.membership_state, mq.role_notes
        FROM member_quartet mq
        JOIN quartet q ON q.id = mq.quartet_id
        WHERE mq.member_id = :member_id
        ORDER BY mq.membership_state, q.name
        """,
        {"member_id": member_id},
    )
    return member


def update_member(member_id: int, values: dict[str, str]) -> None:
    db.execute(
        """
        UPDATE member
        SET
            first_name = :first_name,
            last_name = :last_name,
            preferred_name = :preferred_name,
            status_id = :status_id,
            membership_start_date = :membership_start_date,
            inactive_date = :inactive_date,
            date_of_birth = :date_of_birth,
            date_of_death = :date_of_death,
            anniversary_date = :anniversary_date,
            picture_path = :picture_path,
            notes = :notes,
            updated_at = now()
        WHERE id = :member_id
        """,
        {
            "member_id": member_id,
            "first_name": values["first_name"].strip(),
            "last_name": values["last_name"].strip(),
            "preferred_name": values.get("preferred_name", "").strip() or None,
            "status_id": optional_int(values.get("status_id", "")),
            "membership_start_date": optional_date(values.get("membership_start_date", "")),
            "inactive_date": optional_date(values.get("inactive_date", "")),
            "date_of_birth": optional_date(values.get("date_of_birth", "")),
            "date_of_death": optional_date(values.get("date_of_death", "")),
            "anniversary_date": optional_date(values.get("anniversary_date", "")),
            "picture_path": values.get("picture_path", "").strip() or None,
            "notes": values.get("notes", "").strip() or None,
        },
    )


def add_family_member(
    member_id: int,
    first_name: str,
    last_name: str,
    relationship: str,
    date_of_birth: str,
    email_address: str,
    picture_path: str,
    notes: str,
) -> None:
    normalized_relationship = relationship if relationship in FAMILY_RELATIONSHIPS else "other"
    birth_date = date_of_birth.strip() or None
    db.execute(
        """
        INSERT INTO member_family (
            member_id, first_name, last_name, relationship,
            date_of_birth, email_address, picture_path, notes
        )
        VALUES (
            :member_id, :first_name, :last_name, :relationship,
            :date_of_birth, :email_address, :picture_path, :notes
        )
        """,
        {
            "member_id": member_id,
            "first_name": first_name.strip(),
            "last_name": last_name.strip() or None,
            "relationship": normalized_relationship,
            "date_of_birth": birth_date,
            "email_address": email_address.strip() or None,
            "picture_path": picture_path.strip() or None,
            "notes": notes.strip() or None,
        },
    )


def family_member(member_id: int, family_id: int) -> Optional[dict]:
    return db.fetch_one(
        """
        SELECT *
        FROM member_family
        WHERE id = :family_id
          AND member_id = :member_id
        """,
        {"member_id": member_id, "family_id": family_id},
    )


def update_family_member(
    member_id: int,
    family_id: int,
    first_name: str,
    last_name: str,
    relationship: str,
    date_of_birth: str,
    email_address: str,
    picture_path: str,
    notes: str,
) -> None:
    normalized_relationship = relationship if relationship in FAMILY_RELATIONSHIPS else "other"
    db.execute(
        """
        UPDATE member_family
        SET
            first_name = :first_name,
            last_name = :last_name,
            relationship = :relationship,
            date_of_birth = :date_of_birth,
            email_address = :email_address,
            picture_path = :picture_path,
            notes = :notes,
            updated_at = now()
        WHERE id = :family_id
          AND member_id = :member_id
        """,
        {
            "member_id": member_id,
            "family_id": family_id,
            "first_name": first_name.strip(),
            "last_name": last_name.strip() or None,
            "relationship": normalized_relationship,
            "date_of_birth": optional_date(date_of_birth),
            "email_address": email_address.strip() or None,
            "picture_path": picture_path.strip() or None,
            "notes": notes.strip() or None,
        },
    )


def delete_family_member(member_id: int, family_id: int) -> None:
    db.execute(
        "DELETE FROM member_family WHERE id = :family_id AND member_id = :member_id",
        {"family_id": family_id, "member_id": member_id},
    )


def voice_parts() -> list[dict]:
    return db.fetch_all("SELECT id, part_name FROM voice_part ORDER BY part_name")


def statuses() -> list[dict]:
    return db.fetch_all("SELECT id, status_code FROM membership_status ORDER BY status_code")
