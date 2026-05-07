from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

from jubilaires_membership import db


ROLES = {"member", "administrator"}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return f"pbkdf2_sha256$260000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), digest_hex)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str) -> str:
    return username.strip().lower()


def user_by_id(user_id: int) -> Optional[dict]:
    return db.fetch_one(
        """
        SELECT au.*, m.first_name AS member_first_name, m.last_name AS member_last_name
        FROM app_user au
        LEFT JOIN member m ON m.id = au.member_id
        WHERE au.id = :user_id
        """,
        {"user_id": user_id},
    )


def user_by_username(username: str) -> Optional[dict]:
    return db.fetch_one("SELECT * FROM app_user WHERE username = :username", {"username": normalize_username(username)})


def email_exists(email: str) -> bool:
    return bool(db.fetch_one("SELECT 1 FROM app_user WHERE email = :email", {"email": normalize_email(email)}))


def username_exists(username: str) -> bool:
    return bool(db.fetch_one("SELECT 1 FROM app_user WHERE username = :username", {"username": normalize_username(username)}))


def matching_member(first_name: str, last_name: str, email: str) -> Optional[dict]:
    return db.fetch_one(
        """
        SELECT m.id, m.first_name, m.last_name
        FROM member m
        JOIN member_email me ON me.member_id = m.id
        WHERE lower(m.first_name) = lower(:first_name)
          AND lower(m.last_name) = lower(:last_name)
          AND lower(me.email_address) = lower(:email)
        ORDER BY me.is_primary DESC, me.id
        LIMIT 1
        """,
        {"first_name": first_name.strip(), "last_name": last_name.strip(), "email": normalize_email(email)},
    )


def register_user(first_name: str, last_name: str, email: str, username: str, password: str) -> dict:
    member = matching_member(first_name, last_name, email)
    return db.fetch_one_write(
        """
        INSERT INTO app_user (
            member_id, first_name, last_name, email, username, password_hash, role
        )
        VALUES (
            :member_id, :first_name, :last_name, :email, :username, :password_hash, NULL
        )
        RETURNING id, member_id, first_name, last_name, email, username, role
        """,
        {
            "member_id": member["id"] if member else None,
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": normalize_email(email),
            "username": normalize_username(username),
            "password_hash": hash_password(password),
        },
    )


def authenticate(username: str, password: str) -> Optional[dict]:
    user = user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user


def pending_users() -> list[dict]:
    return db.fetch_all(
        """
        SELECT au.*, m.first_name AS member_first_name, m.last_name AS member_last_name
        FROM app_user au
        LEFT JOIN member m ON m.id = au.member_id
        WHERE au.role IS NULL
        ORDER BY au.created_at
        """
    )


def all_users() -> list[dict]:
    return db.fetch_all(
        """
        SELECT au.*, m.first_name AS member_first_name, m.last_name AS member_last_name
        FROM app_user au
        LEFT JOIN member m ON m.id = au.member_id
        WHERE au.role IS NOT NULL
        ORDER BY au.role NULLS FIRST, au.last_name, au.first_name
        """
    )


def approve_user(user_id: int, role: str, approver_id: int) -> None:
    if role not in ROLES:
        return
    db.execute(
        """
        UPDATE app_user
        SET role = :role,
            approved_at = now(),
            approved_by_user_id = :approver_id,
            updated_at = now()
        WHERE id = :user_id
        """,
        {"user_id": user_id, "role": role, "approver_id": approver_id},
    )


def user_for_member(member_id: int) -> Optional[dict]:
    return db.fetch_one("SELECT * FROM app_user WHERE member_id = :member_id ORDER BY id LIMIT 1", {"member_id": member_id})


def set_password(user_id: int, password: str) -> None:
    db.execute(
        "UPDATE app_user SET password_hash = :password_hash, updated_at = now() WHERE id = :user_id",
        {"user_id": user_id, "password_hash": hash_password(password)},
    )


def upsert_admin(first_name: str, last_name: str, email: str, username: str, password: str) -> dict:
    member = matching_member(first_name, last_name, email)
    return db.fetch_one_write(
        """
        INSERT INTO app_user (
            member_id, first_name, last_name, email, username, password_hash, role, approved_at
        )
        VALUES (
            :member_id, :first_name, :last_name, :email, :username, :password_hash, 'administrator', now()
        )
        ON CONFLICT (email) DO UPDATE SET
            member_id = COALESCE(EXCLUDED.member_id, app_user.member_id),
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            username = EXCLUDED.username,
            password_hash = EXCLUDED.password_hash,
            role = 'administrator',
            approved_at = COALESCE(app_user.approved_at, now()),
            updated_at = now()
        RETURNING id, email, username, role
        """,
        {
            "member_id": member["id"] if member else None,
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": normalize_email(email),
            "username": normalize_username(username),
            "password_hash": hash_password(password),
        },
    )
