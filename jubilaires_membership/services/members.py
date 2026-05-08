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


def optional_bool(value: str | None) -> bool:
    return value in {"1", "true", "on", "yes"}


def dashboard_counts() -> dict:
    counts = db.fetch_one(
        """
        SELECT
            COUNT(DISTINCT m.id) AS total_members,
            COUNT(DISTINCT m.id) FILTER (WHERE lower(ms.status_code) = 'active') AS active_members,
            COUNT(DISTINCT m.id) FILTER (WHERE lower(ms.status_code) = 'active' AND vp.part_name = 'Tenor') AS tenors,
            COUNT(DISTINCT m.id) FILTER (WHERE lower(ms.status_code) = 'active' AND vp.part_name = 'Lead') AS leads,
            COUNT(DISTINCT m.id) FILTER (WHERE lower(ms.status_code) = 'active' AND vp.part_name = 'Baritone') AS baritones,
            COUNT(DISTINCT m.id) FILTER (WHERE lower(ms.status_code) = 'active' AND vp.part_name = 'Bass') AS basses
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
            CASE
                WHEN m.membership_start_date IS NULL THEN NULL
                ELSE GREATEST(
                    0,
                    date_part(
                        'year',
                        age(COALESCE(m.inactive_date, CURRENT_DATE), m.membership_start_date)
                    )::int
                )
            END AS years_active,
            part_summary.part_names,
            ms.status_code,
            primary_phone.phone_number AS primary_phone,
            primary_email.email_address AS primary_email,
            login_user.id AS user_id,
            login_user.username
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
            SELECT id, username
            FROM app_user
            WHERE member_id = m.id
            ORDER BY id
            LIMIT 1
        ) login_user ON true
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
        SELECT
            q.id,
            q.name,
            q.is_active,
            q.formation_date,
            q.deactivation_date,
            q.notes,
            mq.membership_state,
            mq.role_notes
        FROM member_quartet mq
        JOIN quartet q ON q.id = mq.quartet_id
        WHERE mq.member_id = :member_id
        ORDER BY mq.membership_state, q.name
        """,
        {"member_id": member_id},
    )
    member["voice_part_ids"] = [part["id"] for part in member["voice_parts"]]
    member["quartets_by_id"] = {quartet["id"]: quartet for quartet in member["quartets"]}
    member["leadership_roles"] = db.fetch_all(
        """
        SELECT mr.id AS role_id, mr.role_name, mra.start_date, mra.end_date, mra.source_system, mra.notes
        FROM member_role_assignment mra
        JOIN member_role mr ON mr.id = mra.role_id
        WHERE mra.member_id = :member_id
        ORDER BY mr.role_name
        """,
        {"member_id": member_id},
    )
    member["leadership_roles_by_id"] = {role["role_id"]: role for role in member["leadership_roles"]}
    member["emergency_contacts"] = db.fetch_all(
        """
        SELECT *
        FROM member_emergency_contact
        WHERE member_id = :member_id
        ORDER BY id
        """,
        {"member_id": member_id},
    )
    member["external_accounts"] = db.fetch_all(
        """
        SELECT *
        FROM member_external_account
        WHERE member_id = :member_id
        ORDER BY source_system
        """,
        {"member_id": member_id},
    )
    member["classifications"] = db.fetch_all(
        """
        SELECT
            mc.classification_type,
            mc.name,
            mc.source_system,
            mca.source_value
        FROM member_classification_assignment mca
        JOIN member_classification mc ON mc.id = mca.classification_id
        WHERE mca.member_id = :member_id
        ORDER BY mc.classification_type, mc.name
        """,
        {"member_id": member_id},
    )
    return member


def update_member_voice_parts(member_id: int, voice_part_ids: list[int]) -> None:
    db.execute("DELETE FROM member_voice_part WHERE member_id = :member_id", {"member_id": member_id})
    for index, voice_part_id in enumerate(dict.fromkeys(voice_part_ids)):
        db.execute(
            """
            INSERT INTO member_voice_part (member_id, voice_part_id, is_primary)
            VALUES (:member_id, :voice_part_id, :is_primary)
            """,
            {
                "member_id": member_id,
                "voice_part_id": voice_part_id,
                "is_primary": index == 0,
            },
        )


def update_quartet_catalog(quartet_id: int, values: dict[str, str]) -> None:
    db.execute(
        """
        UPDATE quartet
        SET
            is_active = :is_active,
            formation_date = :formation_date,
            deactivation_date = :deactivation_date,
            notes = :notes
        WHERE id = :quartet_id
        """,
        {
            "quartet_id": quartet_id,
            "is_active": optional_bool(values.get("is_active")),
            "formation_date": optional_date(values.get("formation_date", "")),
            "deactivation_date": optional_date(values.get("deactivation_date", "")),
            "notes": values.get("notes", "").strip() or None,
        },
    )


def update_member_quartets(member_id: int, assignments: list[dict[str, str]]) -> None:
    db.execute("DELETE FROM member_quartet WHERE member_id = :member_id", {"member_id": member_id})
    for assignment in assignments:
        db.execute(
            """
            INSERT INTO member_quartet (member_id, quartet_id, membership_state, role_notes)
            VALUES (:member_id, :quartet_id, :membership_state, :role_notes)
            """,
            {
                "member_id": member_id,
                "quartet_id": int(assignment["quartet_id"]),
                "membership_state": assignment["membership_state"] if assignment["membership_state"] in {"primary", "alternate"} else "primary",
                "role_notes": assignment.get("role_notes", "").strip() or None,
            },
        )


def update_member_emails(member_id: int, rows: list[dict[str, str]]) -> None:
    db.execute("DELETE FROM member_email WHERE member_id = :member_id", {"member_id": member_id})
    for row in rows:
        email_address = row.get("email_address", "").strip()
        if not email_address:
            continue
        db.execute(
            """
            INSERT INTO member_email (member_id, email_address, label, is_primary)
            VALUES (:member_id, :email_address, :label, :is_primary)
            """,
            {
                "member_id": member_id,
                "email_address": email_address,
                "label": row.get("label", "").strip() or None,
                "is_primary": optional_bool(row.get("is_primary")),
            },
        )


def update_member_phones(member_id: int, rows: list[dict[str, str]]) -> None:
    db.execute("DELETE FROM member_phone WHERE member_id = :member_id", {"member_id": member_id})
    for row in rows:
        phone_number = row.get("phone_number", "").strip()
        if not phone_number:
            continue
        db.execute(
            """
            INSERT INTO member_phone (member_id, phone_type, phone_number, label, is_primary)
            VALUES (:member_id, :phone_type, :phone_number, :label, :is_primary)
            """,
            {
                "member_id": member_id,
                "phone_type": row.get("phone_type", "").strip() or None,
                "phone_number": phone_number,
                "label": row.get("label", "").strip() or None,
                "is_primary": optional_bool(row.get("is_primary")),
            },
        )


def update_member_addresses(member_id: int, rows: list[dict[str, str]]) -> None:
    db.execute("DELETE FROM member_address WHERE member_id = :member_id", {"member_id": member_id})
    for row in rows:
        has_address = any(row.get(field, "").strip() for field in ("street", "city", "state", "postal_code", "raw_address"))
        if not has_address:
            continue
        db.execute(
            """
            INSERT INTO member_address (
                member_id, address_type, street, city, state, postal_code, country, raw_address, is_primary
            )
            VALUES (
                :member_id, :address_type, :street, :city, :state, :postal_code, :country, :raw_address, :is_primary
            )
            """,
            {
                "member_id": member_id,
                "address_type": row.get("address_type", "").strip() or "primary",
                "street": row.get("street", "").strip() or None,
                "city": row.get("city", "").strip() or None,
                "state": row.get("state", "").strip() or None,
                "postal_code": row.get("postal_code", "").strip() or None,
                "country": row.get("country", "").strip() or "USA",
                "raw_address": row.get("raw_address", "").strip() or None,
                "is_primary": optional_bool(row.get("is_primary")),
            },
        )


def update_member_role_assignments(member_id: int, assignments: list[dict[str, str]]) -> None:
    db.execute("DELETE FROM member_role_assignment WHERE member_id = :member_id", {"member_id": member_id})
    for assignment in assignments:
        role_name = assignment.get("role_name", "").strip()
        role_id = optional_int(assignment.get("role_id", ""))
        if not role_id and role_name:
            role_id = db.fetch_one(
                """
                INSERT INTO member_role (role_name)
                VALUES (:role_name)
                ON CONFLICT (role_name) DO UPDATE SET role_name = EXCLUDED.role_name
                RETURNING id
                """,
                {"role_name": role_name},
            )["id"]
        if not role_id:
            continue
        db.execute(
            """
            INSERT INTO member_role_assignment (
                member_id, role_id, start_date, end_date, source_system, notes
            )
            VALUES (
                :member_id, :role_id, :start_date, :end_date, :source_system, :notes
            )
            """,
            {
                "member_id": member_id,
                "role_id": role_id,
                "start_date": optional_date(assignment.get("start_date", "")),
                "end_date": optional_date(assignment.get("end_date", "")),
                "source_system": assignment.get("source_system", "").strip() or "Manual",
                "notes": assignment.get("notes", "").strip() or None,
            },
        )


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


def delete_member(member_id: int) -> None:
    db.execute("DELETE FROM member WHERE id = :member_id", {"member_id": member_id})


def update_member_picture_path(member_id: int, picture_path: str) -> None:
    db.execute(
        """
        UPDATE member
        SET picture_path = :picture_path,
            updated_at = now()
        WHERE id = :member_id
        """,
        {"member_id": member_id, "picture_path": picture_path.strip() or None},
    )


def update_family_picture_path(member_id: int, family_id: int, picture_path: str) -> None:
    db.execute(
        """
        UPDATE member_family
        SET picture_path = :picture_path,
            updated_at = now()
        WHERE id = :family_id
          AND member_id = :member_id
        """,
        {"member_id": member_id, "family_id": family_id, "picture_path": picture_path.strip() or None},
    )


def assigned_picture_paths() -> set[str]:
    rows = db.fetch_all(
        """
        SELECT picture_path
        FROM member
        WHERE picture_path IS NOT NULL
          AND picture_path <> ''
        UNION
        SELECT picture_path
        FROM member_family
        WHERE picture_path IS NOT NULL
          AND picture_path <> ''
        """
    )
    return {row["picture_path"] for row in rows}


def photo_assignments() -> dict[str, dict]:
    rows = db.fetch_all(
        """
        SELECT
            'member' AS target_type,
            m.id AS member_id,
            NULL::integer AS family_id,
            m.picture_path,
            m.first_name,
            m.last_name,
            NULL::text AS relationship,
            NULL::text AS member_first_name,
            NULL::text AS member_last_name
        FROM member m
        WHERE m.picture_path IS NOT NULL
          AND m.picture_path <> ''
        UNION ALL
        SELECT
            'family' AS target_type,
            mf.member_id,
            mf.id AS family_id,
            mf.picture_path,
            mf.first_name,
            mf.last_name,
            mf.relationship,
            m.first_name AS member_first_name,
            m.last_name AS member_last_name
        FROM member_family mf
        JOIN member m ON m.id = mf.member_id
        WHERE mf.picture_path IS NOT NULL
          AND mf.picture_path <> ''
        """
    )
    return {row["picture_path"]: row for row in rows}


def clear_picture_path(picture_path: str) -> None:
    db.execute(
        """
        UPDATE member
        SET picture_path = NULL,
            updated_at = now()
        WHERE picture_path = :picture_path
        """,
        {"picture_path": picture_path},
    )
    db.execute(
        """
        UPDATE member_family
        SET picture_path = NULL,
            updated_at = now()
        WHERE picture_path = :picture_path
        """,
        {"picture_path": picture_path},
    )


def member_options() -> list[dict]:
    return db.fetch_all(
        """
        SELECT id, first_name, last_name
        FROM member
        ORDER BY last_name, first_name
        """
    )


def family_options() -> list[dict]:
    return db.fetch_all(
        """
        SELECT
            mf.id,
            mf.member_id,
            mf.first_name,
            mf.last_name,
            mf.relationship,
            m.first_name AS member_first_name,
            m.last_name AS member_last_name
        FROM member_family mf
        JOIN member m ON m.id = mf.member_id
        ORDER BY m.last_name, m.first_name, mf.first_name, mf.last_name
        """
    )


def family_owner_id(family_id: int) -> int | None:
    row = db.fetch_one("SELECT member_id FROM member_family WHERE id = :family_id", {"family_id": family_id})
    return row["member_id"] if row else None


def voice_parts() -> list[dict]:
    return db.fetch_all("SELECT id, part_name FROM voice_part ORDER BY part_name")


def quartets() -> list[dict]:
    return db.fetch_all(
        """
        SELECT id, name, is_active, formation_date, deactivation_date, picture_path, notes
        FROM quartet
        ORDER BY is_active DESC, name
        """
    )


def quartet_rows() -> list[dict]:
    return db.fetch_all(
        """
        SELECT
            q.id,
            q.name,
            q.is_active,
            q.formation_date,
            q.deactivation_date,
            q.picture_path,
            q.notes,
            COUNT(mq.member_id) FILTER (WHERE mq.membership_state = 'primary') AS primary_count,
            COUNT(mq.member_id) FILTER (WHERE mq.membership_state = 'alternate') AS alternate_count,
            string_agg(
                trim(concat_ws(' ', m.first_name, m.last_name)) || ' (' || mq.membership_state || ')',
                ', ' ORDER BY mq.membership_state DESC, m.last_name, m.first_name
            ) AS member_summary
        FROM quartet q
        LEFT JOIN member_quartet mq ON mq.quartet_id = q.id
        LEFT JOIN member m ON m.id = mq.member_id
        GROUP BY q.id
        ORDER BY q.is_active DESC, q.name
        """
    )


def quartet_detail(quartet_id: int) -> Optional[dict]:
    quartet = db.fetch_one(
        """
        SELECT id, name, is_active, formation_date, deactivation_date, picture_path, notes
        FROM quartet
        WHERE id = :quartet_id
        """,
        {"quartet_id": quartet_id},
    )
    if not quartet:
        return None
    quartet["members"] = db.fetch_all(
        """
        SELECT
            mq.member_id,
            mq.membership_state,
            mq.voice_part_id,
            quartet_vp.part_name AS quartet_part_name,
            mq.role_notes,
            m.first_name,
            m.last_name,
            m.picture_path,
            part_summary.part_names,
            phone_summary.phone_numbers,
            email_summary.email_addresses,
            address_summary.mailing_addresses
        FROM member_quartet mq
        JOIN member m ON m.id = mq.member_id
        LEFT JOIN voice_part quartet_vp ON quartet_vp.id = mq.voice_part_id
        LEFT JOIN LATERAL (
            SELECT string_agg(vp.part_name, ', ' ORDER BY mvp.is_primary DESC, vp.part_name) AS part_names
            FROM member_voice_part mvp
            JOIN voice_part vp ON vp.id = mvp.voice_part_id
            WHERE mvp.member_id = m.id
        ) part_summary ON true
        LEFT JOIN LATERAL (
            SELECT string_agg(
                trim(concat_ws(' ', COALESCE(label, phone_type), phone_number)),
                ', ' ORDER BY is_primary DESC, id
            ) AS phone_numbers
            FROM member_phone
            WHERE member_id = m.id
        ) phone_summary ON true
        LEFT JOIN LATERAL (
            SELECT string_agg(
                trim(concat_ws(' ', COALESCE(label, ''), email_address)),
                ', ' ORDER BY is_primary DESC, id
            ) AS email_addresses
            FROM member_email
            WHERE member_id = m.id
        ) email_summary ON true
        LEFT JOIN LATERAL (
            SELECT string_agg(
                CASE
                    WHEN NULLIF(raw_address, '') IS NOT NULL THEN raw_address
                    ELSE trim(concat_ws(', ', NULLIF(street, ''), NULLIF(city, ''), NULLIF(state, ''), NULLIF(postal_code, '')))
                END,
                ' | ' ORDER BY is_primary DESC, id
            ) AS mailing_addresses
            FROM member_address
            WHERE member_id = m.id
        ) address_summary ON true
        WHERE mq.quartet_id = :quartet_id
        ORDER BY
            CASE mq.membership_state WHEN 'primary' THEN 1 ELSE 2 END,
            quartet_vp.part_name NULLS LAST,
            m.last_name,
            m.first_name
        """,
        {"quartet_id": quartet_id},
    )
    quartet["members_by_id"] = {member["member_id"]: member for member in quartet["members"]}
    return quartet


def primary_quartet_member_ids(quartet_id: int) -> set[int]:
    rows = db.fetch_all(
        """
        SELECT member_id
        FROM member_quartet
        WHERE quartet_id = :quartet_id
          AND membership_state = 'primary'
        """,
        {"quartet_id": quartet_id},
    )
    return {row["member_id"] for row in rows}


def create_quartet(values: dict[str, str]) -> int:
    row = db.fetch_one_write(
        """
        INSERT INTO quartet (name, is_active, formation_date, deactivation_date, notes)
        VALUES (:name, :is_active, :formation_date, :deactivation_date, :notes)
        RETURNING id
        """,
        {
            "name": values["name"].strip(),
            "is_active": optional_bool(values.get("is_active")),
            "formation_date": optional_date(values.get("formation_date", "")),
            "deactivation_date": optional_date(values.get("deactivation_date", "")),
            "notes": values.get("notes", "").strip() or None,
        },
    )
    return row["id"]


def update_quartet(quartet_id: int, values: dict[str, str]) -> None:
    db.execute(
        """
        UPDATE quartet
        SET
            name = :name,
            is_active = :is_active,
            formation_date = :formation_date,
            deactivation_date = :deactivation_date,
            notes = :notes
        WHERE id = :quartet_id
        """,
        {
            "quartet_id": quartet_id,
            "name": values["name"].strip(),
            "is_active": optional_bool(values.get("is_active")),
            "formation_date": optional_date(values.get("formation_date", "")),
            "deactivation_date": optional_date(values.get("deactivation_date", "")),
            "notes": values.get("notes", "").strip() or None,
        },
    )


def delete_quartet(quartet_id: int) -> None:
    db.execute("DELETE FROM quartet WHERE id = :quartet_id", {"quartet_id": quartet_id})


def update_quartet_members(quartet_id: int, assignments: list[dict[str, str]]) -> None:
    db.execute("DELETE FROM member_quartet WHERE quartet_id = :quartet_id", {"quartet_id": quartet_id})
    for assignment in assignments:
        member_id = optional_int(assignment.get("member_id", ""))
        if not member_id:
            continue
        membership_state = assignment.get("membership_state", "primary")
        if membership_state not in {"primary", "alternate"}:
            membership_state = "primary"
        db.execute(
            """
            INSERT INTO member_quartet (member_id, quartet_id, membership_state, voice_part_id, role_notes)
            VALUES (:member_id, :quartet_id, :membership_state, :voice_part_id, :role_notes)
            """,
            {
                "member_id": member_id,
                "quartet_id": quartet_id,
                "membership_state": membership_state,
                "voice_part_id": optional_int(assignment.get("voice_part_id", "")),
                "role_notes": assignment.get("role_notes", "").strip() or None,
            },
        )


def upsert_quartet_member(quartet_id: int, values: dict[str, str]) -> None:
    member_id = optional_int(values.get("member_id", ""))
    if not member_id:
        return
    membership_state = values.get("membership_state", "primary")
    if membership_state not in {"primary", "alternate"}:
        membership_state = "primary"
    db.execute(
        """
        INSERT INTO member_quartet (member_id, quartet_id, membership_state, voice_part_id, role_notes)
        VALUES (:member_id, :quartet_id, :membership_state, :voice_part_id, :role_notes)
        ON CONFLICT (member_id, quartet_id) DO UPDATE
        SET
            membership_state = EXCLUDED.membership_state,
            voice_part_id = EXCLUDED.voice_part_id,
            role_notes = EXCLUDED.role_notes
        """,
        {
            "member_id": member_id,
            "quartet_id": quartet_id,
            "membership_state": membership_state,
            "voice_part_id": optional_int(values.get("voice_part_id", "")),
            "role_notes": values.get("role_notes", "").strip() or None,
        },
    )


def delete_quartet_member(quartet_id: int, member_id: int) -> None:
    db.execute(
        """
        DELETE FROM member_quartet
        WHERE quartet_id = :quartet_id
          AND member_id = :member_id
        """,
        {"quartet_id": quartet_id, "member_id": member_id},
    )


def update_quartet_picture_path(quartet_id: int, picture_path: str) -> None:
    db.execute(
        """
        UPDATE quartet
        SET picture_path = :picture_path
        WHERE id = :quartet_id
        """,
        {"quartet_id": quartet_id, "picture_path": picture_path.strip() or None},
    )


def member_roles() -> list[dict]:
    return db.fetch_all("SELECT id, role_name FROM member_role ORDER BY role_name")


def statuses() -> list[dict]:
    return db.fetch_all("SELECT id, status_code FROM membership_status ORDER BY status_code")
