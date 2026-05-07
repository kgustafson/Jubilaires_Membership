from __future__ import annotations

import hashlib
import hmac
import os
import base64
import secrets
from io import BytesIO
from typing import Optional
from urllib.parse import quote

import pyotp
import qrcode

from jubilaires_membership import db


ROLES = {"member", "administrator"}
TOTP_ISSUER = "Fairfax Jubil-Aires"


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


def email_exists_for_other_user(email: str, user_id: int) -> bool:
    return bool(
        db.fetch_one(
            "SELECT 1 FROM app_user WHERE email = :email AND id <> :user_id",
            {"email": normalize_email(email), "user_id": user_id},
        )
    )


def username_exists(username: str) -> bool:
    return bool(db.fetch_one("SELECT 1 FROM app_user WHERE username = :username", {"username": normalize_username(username)}))


def username_exists_for_other_user(username: str, user_id: int) -> bool:
    return bool(
        db.fetch_one(
            "SELECT 1 FROM app_user WHERE username = :username AND id <> :user_id",
            {"username": normalize_username(username), "user_id": user_id},
        )
    )


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


def record_login(user_id: int) -> None:
    db.execute(
        "UPDATE app_user SET last_login_at = now(), updated_at = now() WHERE id = :user_id",
        {"user_id": user_id},
    )


def new_totp_secret() -> str:
    return pyotp.random_base32()


def ensure_totp_secret(user_id: int) -> str:
    user = user_by_id(user_id)
    if user and user.get("totp_secret"):
        return user["totp_secret"]
    secret = new_totp_secret()
    db.execute(
        "UPDATE app_user SET totp_secret = :secret, updated_at = now() WHERE id = :user_id",
        {"user_id": user_id, "secret": secret},
    )
    return secret


def totp_uri(user: dict, secret: str) -> str:
    account_name = quote(f"{TOTP_ISSUER}:{user['username']}")
    issuer = quote(TOTP_ISSUER)
    return f"otpauth://totp/{account_name}?secret={secret}&issuer={issuer}"


def qr_code_data_url(value: str) -> str:
    image = qrcode.make(value)
    output = BytesIO()
    image.save(output, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(output.getvalue()).decode('ascii')}"


def verify_totp(secret: str, code: str) -> bool:
    normalized = "".join(char for char in code if char.isdigit())
    if len(normalized) != 6:
        return False
    return bool(pyotp.TOTP(secret).verify(normalized, valid_window=1))


def generate_recovery_codes(user_id: int, count: int = 10) -> list[str]:
    db.execute("DELETE FROM app_user_recovery_code WHERE user_id = :user_id", {"user_id": user_id})
    codes = []
    for _ in range(count):
        code = "-".join(secrets.token_hex(2).upper() for _ in range(3))
        codes.append(code)
        db.execute(
            "INSERT INTO app_user_recovery_code (user_id, code_hash) VALUES (:user_id, :code_hash)",
            {"user_id": user_id, "code_hash": hash_password(code)},
        )
    return codes


def enable_totp(user_id: int) -> list[str]:
    db.execute(
        "UPDATE app_user SET totp_enabled_at = now(), updated_at = now() WHERE id = :user_id",
        {"user_id": user_id},
    )
    return generate_recovery_codes(user_id)


def consume_recovery_code(user_id: int, code: str) -> bool:
    normalized = code.strip().upper()
    if not normalized:
        return False
    rows = db.fetch_all(
        "SELECT id, code_hash FROM app_user_recovery_code WHERE user_id = :user_id AND used_at IS NULL ORDER BY id",
        {"user_id": user_id},
    )
    for row in rows:
        if verify_password(normalized, row["code_hash"]):
            db.execute(
                "UPDATE app_user_recovery_code SET used_at = now() WHERE id = :id",
                {"id": row["id"]},
            )
            return True
    return False


def reset_two_factor(user_id: int) -> None:
    db.execute("DELETE FROM app_user_recovery_code WHERE user_id = :user_id", {"user_id": user_id})
    db.execute(
        """
        UPDATE app_user
        SET totp_secret = NULL,
            totp_enabled_at = NULL,
            updated_at = now()
        WHERE id = :user_id
        """,
        {"user_id": user_id},
    )


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


def update_account(user_id: int, first_name: str, last_name: str, email: str, username: str, password: str = "") -> None:
    params = {
        "user_id": user_id,
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": normalize_email(email),
        "username": normalize_username(username),
    }
    password_sql = ""
    if password:
        password_sql = ", password_hash = :password_hash"
        params["password_hash"] = hash_password(password)
    db.execute(
        f"""
        UPDATE app_user
        SET first_name = :first_name,
            last_name = :last_name,
            email = :email,
            username = :username,
            updated_at = now()
            {password_sql}
        WHERE id = :user_id
        """,
        params,
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
