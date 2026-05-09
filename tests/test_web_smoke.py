from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest
from itsdangerous import TimestampSigner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("JUBILAIRES_SMOKE_BASE_URL", "http://127.0.0.1:8091").rstrip("/")
SESSION_SECRET = os.environ.get("JUBILAIRES_SESSION_SECRET", "local-dev-change-me")
ADMIN_USER_ID = int(os.environ.get("JUBILAIRES_SMOKE_ADMIN_USER_ID", "1"))
MEMBER_ID = int(os.environ.get("JUBILAIRES_SMOKE_MEMBER_ID", "27"))


def admin_session_cookie() -> str:
    payload = base64.b64encode(json.dumps({"user_id": ADMIN_USER_ID}).encode()).decode()
    return TimestampSigner(SESSION_SECRET).sign(payload).decode()


@pytest.fixture(scope="session")
def public_client() -> httpx.Client:
    with httpx.Client(base_url=BASE_URL, follow_redirects=False, timeout=10) as client:
        yield client


@pytest.fixture(scope="session")
def admin_client() -> httpx.Client:
    cookies = {"session": admin_session_cookie()}
    with httpx.Client(base_url=BASE_URL, follow_redirects=False, timeout=10, cookies=cookies) as client:
        yield client


def assert_page(client: httpx.Client, path: str, expected_fragments: list[str]) -> str:
    response = client.get(path)
    assert response.status_code == 200
    for fragment in expected_fragments:
        assert fragment in response.text
    return response.text


def test_login_page_renders(public_client: httpx.Client):
    body = assert_page(public_client, "/login", ["Login", "Register"])
    assert "username" in body.lower()


def test_register_page_renders(public_client: httpx.Client):
    assert_page(public_client, "/register", ["Register", "username"])


def test_protected_dashboard_redirects_to_login_without_session(public_client: httpx.Client):
    response = public_client.get("/")
    assert response.status_code == 303
    assert "/login?next=/" in response.headers["location"]


def test_bad_login_stays_on_login_with_error(public_client: httpx.Client):
    response = public_client.post(
        "/login",
        data={"username": "definitely-not-a-user", "password": "not-the-password", "next": "/"},
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


def test_dashboard_roster_renders(admin_client: httpx.Client):
    body = assert_page(admin_client, "/", ["Dashboard", "Roster", "Show Inactive", "data-member-table"])
    assert "(703) 472-7508" in body


def test_account_page_renders(admin_client: httpx.Client):
    assert_page(admin_client, "/account", ["Account", "Username", "Change Password"])


def test_member_detail_renders_core_sections(admin_client: httpx.Client):
    assert_page(
        admin_client,
        f"/members/{MEMBER_ID}",
        ["member-contact-card", "Birthdays", "Quartets", "Status", "Family", "Current Roles", "Prior Roles"],
    )


def test_member_edit_renders_editing_modals(admin_client: httpx.Client):
    assert_page(
        admin_client,
        f"/members/{MEMBER_ID}/edit",
        [
            "Voice Parts",
            "Quartets",
            "Member Roles",
            "Email",
            "Phones",
            "Addresses",
            "data-photo-rotate-step",
        ],
    )


def test_admin_user_page_renders(admin_client: httpx.Client):
    assert_page(admin_client, "/admin/users", ["User Administration", "Pending Registrations", "Approved Users"])


def test_database_admin_page_renders_backup_restore_controls(admin_client: httpx.Client):
    assert_page(admin_client, "/admin/database", ["Database Backup", "Create Backup", "Restore"])


def test_quartet_management_renders_crud_and_photo_controls(admin_client: httpx.Client):
    assert_page(admin_client, "/quartets", ["Quartet Management", "New Quartet", "Add Member", "data-photo-rotate-step"])


def test_photo_review_renders_assignment_and_rotation_controls(admin_client: httpx.Client):
    assert_page(admin_client, "/photos/unassigned", ["Photo Review", "Assign To", "Save Rotation"])


def test_logout_redirects_to_login(admin_client: httpx.Client):
    response = admin_client.post("/logout")
    assert response.status_code == 303
    assert "/login?logged_out=1" in response.headers["location"]


@pytest.mark.skipif(
    os.environ.get("JUBILAIRES_RUN_BACKUP_SMOKE") != "1",
    reason="Set JUBILAIRES_RUN_BACKUP_SMOKE=1 to create a backup during smoke tests.",
)
def test_optional_database_backup_post(admin_client: httpx.Client):
    response = admin_client.post("/admin/database/backup")
    assert response.status_code == 200
    assert "Created backup" in response.text


def test_backup_and_restore_scripts_exist_and_parse():
    scripts = [
        PROJECT_ROOT / "scripts" / "backup_database.sh",
        PROJECT_ROOT / "scripts" / "restore_database.sh",
    ]
    for script in scripts:
        assert script.exists()
        assert os.access(script, os.X_OK)
        result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
