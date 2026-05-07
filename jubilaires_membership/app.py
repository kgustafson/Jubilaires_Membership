from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from jubilaires_membership.services import auth, backups, members, photos


app = FastAPI(title="Jubilaires Membership")
APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parent
app.mount("/static", StaticFiles(directory=str(APP_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))
PUBLIC_PATHS = {"/login", "/register", "/two-factor/setup", "/two-factor/verify"}


def current_user(request: Request) -> dict | None:
    user_id = request.session.get("user_id")
    return auth.user_by_id(int(user_id)) if user_id else None


def pending_two_factor_user(request: Request) -> dict | None:
    user_id = request.session.get("pending_2fa_user_id")
    return auth.user_by_id(int(user_id)) if user_id else None


def is_admin(user: dict | None) -> bool:
    return bool(user and user.get("role") == "administrator")


def require_admin(request: Request) -> dict:
    user = current_user(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


def can_edit_member(user: dict | None, member_id: int) -> bool:
    return is_admin(user) or bool(user and user.get("member_id") == member_id)


def require_member_editor(request: Request, member_id: int) -> dict:
    user = current_user(request)
    if not can_edit_member(user, member_id):
        raise HTTPException(status_code=403, detail="You can only edit your own member information.")
    return user


def can_manage_quartet(user: dict | None, quartet_id: int) -> bool:
    return is_admin(user) or bool(
        user
        and user.get("member_id")
        and int(user["member_id"]) in members.primary_quartet_member_ids(quartet_id)
    )


def require_quartet_manager(request: Request, quartet_id: int) -> dict:
    user = current_user(request)
    if not can_manage_quartet(user, quartet_id):
        raise HTTPException(status_code=403, detail="Only administrators and primary quartet members can modify this quartet.")
    return user


def view_context(request: Request, **values):
    values.setdefault("current_user", current_user(request))
    return values


def complete_login(request: Request, user: dict) -> RedirectResponse:
    next_url = safe_redirect_path(request.session.get("login_next"))
    request.session.clear()
    request.session["user_id"] = user["id"]
    auth.record_login(user["id"])
    return RedirectResponse(url=next_url, status_code=303)


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static") or path in PUBLIC_PATHS:
        return await call_next(request)
    if not request.session.get("user_id"):
        return RedirectResponse(url=f"/login?next={path}", status_code=303)
    return await call_next(request)


app.add_middleware(SessionMiddleware, secret_key=os.environ.get("JUBILAIRES_SESSION_SECRET", "local-dev-change-me"))


def safe_redirect_path(value: str | None) -> str:
    value = value or "/"
    return value if value.startswith("/") and not value.startswith("//") else "/"


def application_version() -> str:
    version_file = PROJECT_ROOT / "version.md"
    if not version_file.exists():
        return "v0.0.0"

    for line in version_file.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value.startswith("v"):
            return value
    return "v0.0.0"


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        view_context(
            request,
            counts=members.dashboard_counts(),
            members=members.member_rows(),
            app_version=application_version(),
        ),
    )


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"next_url": request.query_params.get("next", "/")})


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username") or ""
    password = form.get("password") or ""
    user = auth.authenticate(username, password)
    if not user:
        return templates.TemplateResponse(request, "login.html", {"error": "Invalid username or password.", "next_url": form.get("next") or "/"})
    if not user.get("role"):
        return templates.TemplateResponse(request, "login.html", {"error": "Your registration is awaiting administrator approval.", "next_url": form.get("next") or "/"})
    if user.get("role") == "administrator":
        request.session.clear()
        request.session["pending_2fa_user_id"] = user["id"]
        request.session["login_next"] = safe_redirect_path(form.get("next"))
        if user.get("totp_enabled_at"):
            return RedirectResponse(url="/two-factor/verify", status_code=303)
        return RedirectResponse(url="/two-factor/setup", status_code=303)
    request.session["login_next"] = safe_redirect_path(form.get("next"))
    return complete_login(request, user)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login?logged_out=1", status_code=303)


@app.get("/two-factor/setup", response_class=HTMLResponse)
def two_factor_setup_form(request: Request):
    user = pending_two_factor_user(request)
    if not user or user.get("role") != "administrator":
        return RedirectResponse(url="/login", status_code=303)
    if user.get("totp_enabled_at"):
        return RedirectResponse(url="/two-factor/verify", status_code=303)
    secret = auth.ensure_totp_secret(user["id"])
    uri = auth.totp_uri(user, secret)
    return templates.TemplateResponse(
        request,
        "two_factor_setup.html",
        {"current_user": None, "secret": secret, "qr_code_data_url": auth.qr_code_data_url(uri), "otpauth_uri": uri},
    )


@app.post("/two-factor/setup", response_class=HTMLResponse)
async def two_factor_setup(request: Request):
    user = pending_two_factor_user(request)
    if not user or user.get("role") != "administrator":
        return RedirectResponse(url="/login", status_code=303)
    form = await request.form()
    secret = auth.ensure_totp_secret(user["id"])
    if not auth.verify_totp(secret, form.get("code") or ""):
        uri = auth.totp_uri(user, secret)
        return templates.TemplateResponse(
            request,
            "two_factor_setup.html",
            {
                "current_user": None,
                "secret": secret,
                "qr_code_data_url": auth.qr_code_data_url(uri),
                "otpauth_uri": uri,
                "error": "Invalid authentication code.",
            },
        )
    recovery_codes = auth.enable_totp(user["id"])
    complete_login(request, user)
    return templates.TemplateResponse(
        request,
        "two_factor_setup.html",
        {"current_user": user, "setup_complete": True, "recovery_codes": recovery_codes},
    )


@app.get("/two-factor/verify", response_class=HTMLResponse)
def two_factor_verify_form(request: Request):
    user = pending_two_factor_user(request)
    if not user or user.get("role") != "administrator":
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "two_factor_verify.html", {"current_user": None})


@app.post("/two-factor/verify", response_class=HTMLResponse)
async def two_factor_verify(request: Request):
    user = pending_two_factor_user(request)
    if not user or user.get("role") != "administrator":
        return RedirectResponse(url="/login", status_code=303)
    form = await request.form()
    code = form.get("code") or ""
    valid_totp = bool(user.get("totp_secret") and auth.verify_totp(user["totp_secret"], code))
    valid_recovery = auth.consume_recovery_code(user["id"], code)
    if not valid_totp and not valid_recovery:
        return templates.TemplateResponse(request, "two_factor_verify.html", {"current_user": None, "error": "Invalid authentication or recovery code."})
    return complete_login(request, user)


@app.get("/account", response_class=HTMLResponse)
def account_form(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login?next=/account", status_code=303)
    return templates.TemplateResponse(request, "account.html", view_context(request, account=user))


@app.post("/account", response_class=HTMLResponse)
async def update_account(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login?next=/account", status_code=303)
    form = await request.form()
    values = {key: (form.get(key) or "").strip() for key in ("first_name", "last_name", "email", "username")}
    password = form.get("password") or ""
    confirm_password = form.get("confirm_password") or ""
    if not all(values.values()):
        return templates.TemplateResponse(request, "account.html", view_context(request, account={**user, **values}, error="First name, last name, email, and username are required."))
    if auth.email_exists_for_other_user(values["email"], user["id"]):
        return templates.TemplateResponse(request, "account.html", view_context(request, account={**user, **values}, error="That email is already used by another account."))
    if auth.username_exists_for_other_user(values["username"], user["id"]):
        return templates.TemplateResponse(request, "account.html", view_context(request, account={**user, **values}, error="That username already exists. Choose another username."))
    if password or confirm_password:
        if not password or password != confirm_password:
            return templates.TemplateResponse(request, "account.html", view_context(request, account={**user, **values}, error="Passwords do not match."))
    auth.update_account(user["id"], values["first_name"], values["last_name"], values["email"], values["username"], password)
    return RedirectResponse(url="/account?saved=1", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(request, "register.html", {})


@app.post("/register", response_class=HTMLResponse)
async def register(request: Request):
    form = await request.form()
    values = {key: (form.get(key) or "").strip() for key in ("first_name", "last_name", "email", "username")}
    password = form.get("password") or ""
    confirm_password = form.get("confirm_password") or ""
    if not all(values.values()) or not password:
        return templates.TemplateResponse(request, "register.html", {"error": "All fields are required.", "values": values})
    if password != confirm_password:
        return templates.TemplateResponse(request, "register.html", {"error": "Passwords do not match.", "values": values})
    if auth.email_exists(values["email"]):
        return templates.TemplateResponse(request, "register.html", {"error": "That email already has a login.", "values": values})
    if auth.username_exists(values["username"]):
        return templates.TemplateResponse(request, "register.html", {"error": "That username already exists. Choose another username.", "values": values})
    auth.register_user(values["first_name"], values["last_name"], values["email"], values["username"], password)
    return templates.TemplateResponse(request, "register.html", {"registered": True})


@app.get("/admin/users", response_class=HTMLResponse)
def user_admin(request: Request):
    require_admin(request)
    return templates.TemplateResponse(
        request,
        "user_admin.html",
        view_context(request, pending_users=auth.pending_users(), users=auth.all_users()),
    )


@app.post("/admin/users/{user_id}/approve")
async def approve_user(request: Request, user_id: int):
    admin = require_admin(request)
    form = await request.form()
    auth.approve_user(user_id, form.get("role") or "", admin["id"])
    return RedirectResponse(url="/admin/users?approved=1", status_code=303)


@app.post("/admin/users/{user_id}/password")
async def change_user_password(request: Request, user_id: int):
    require_admin(request)
    form = await request.form()
    password = form.get("password") or ""
    confirm_password = form.get("confirm_password") or ""
    return_to = safe_redirect_path(form.get("return_to") or "/")
    if not password or password != confirm_password:
        return RedirectResponse(url=f"{return_to}?password_error=1", status_code=303)
    auth.set_password(user_id, password)
    return RedirectResponse(url=f"{return_to}?password_changed=1", status_code=303)


@app.post("/admin/users/{user_id}/reset-two-factor")
async def reset_user_two_factor(request: Request, user_id: int):
    require_admin(request)
    auth.reset_two_factor(user_id)
    return RedirectResponse(url="/admin/users?two_factor_reset=1", status_code=303)


@app.get("/admin/database", response_class=HTMLResponse)
def database_admin(request: Request):
    require_admin(request)
    return templates.TemplateResponse(
        request,
        "admin_database.html",
        view_context(request, backups=backups.list_backups()),
    )


@app.post("/admin/database/backup", response_class=HTMLResponse)
def create_database_backup(request: Request):
    require_admin(request)
    try:
        backup = backups.create_backup()
        message = f"Created backup {backup['name']}."
        error = ""
    except backups.DatabaseBackupError as exc:
        message = ""
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "admin_database.html",
        view_context(request, backups=backups.list_backups(), message=message, error=error),
    )


@app.post("/admin/database/restore", response_class=HTMLResponse)
async def restore_database_backup(request: Request):
    require_admin(request)
    form = await request.form()
    upload = form.get("backup_file")
    backup_name = (form.get("backup_name") or "").strip()
    try:
        if hasattr(upload, "filename") and upload.filename and hasattr(upload, "file"):
            backups.restore_uploaded_backup(upload.file)
            message = f"Restored database from uploaded file {upload.filename}."
        elif backup_name:
            backups.restore_backup(backup_name)
            message = f"Restored database from backup {backup_name}."
        else:
            raise backups.DatabaseBackupError("Choose a backup file before restoring.")
        error = ""
    except backups.DatabaseBackupError as exc:
        message = ""
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "admin_database.html",
        view_context(request, backups=backups.list_backups(), message=message, error=error),
    )


@app.get("/quartets", response_class=HTMLResponse)
def quartet_management(request: Request):
    user = current_user(request)
    quartet_rows = members.quartet_rows()
    for index, quartet in enumerate(quartet_rows):
        quartet_rows[index] = {**quartet, **(members.quartet_detail(quartet["id"]) or {})}
    manageable_quartet_ids = {quartet["id"] for quartet in quartet_rows if can_manage_quartet(user, quartet["id"])}
    return templates.TemplateResponse(
        request,
        "quartets.html",
        view_context(
            request,
            quartets=quartet_rows,
            member_options=members.member_options(),
            voice_parts=members.voice_parts(),
            manageable_quartet_ids=manageable_quartet_ids,
        ),
    )


@app.post("/quartets")
async def create_quartet(request: Request):
    require_admin(request)
    form = await request.form()
    name = (form.get("name") or "").strip()
    if not name:
        return RedirectResponse(url="/quartets?name_required=1", status_code=303)
    quartet_id = members.create_quartet({key: str(form.get(key) or "") for key in form.keys()})
    return RedirectResponse(url=f"/quartets?created={quartet_id}", status_code=303)


@app.post("/quartets/{quartet_id}")
async def update_quartet(request: Request, quartet_id: int):
    require_quartet_manager(request, quartet_id)
    if not members.quartet_detail(quartet_id):
        raise HTTPException(status_code=404, detail="Quartet not found.")
    form = await request.form()
    name = (form.get("name") or "").strip()
    if not name:
        return RedirectResponse(url="/quartets?name_required=1", status_code=303)
    members.update_quartet(quartet_id, {key: str(form.get(key) or "") for key in form.keys()})
    return RedirectResponse(url=f"/quartets?saved={quartet_id}", status_code=303)


@app.post("/quartets/{quartet_id}/members")
async def update_quartet_members(request: Request, quartet_id: int):
    require_quartet_manager(request, quartet_id)
    if not members.quartet_detail(quartet_id):
        raise HTTPException(status_code=404, detail="Quartet not found.")
    form = await request.form()
    selected_member_ids = {str(value) for value in form.getlist("member_ids")}
    assignments = []
    for member in members.member_options():
        member_id = str(member["id"])
        if member_id in selected_member_ids:
            assignments.append(
                {
                    "member_id": member_id,
                    "membership_state": form.get(f"member_{member_id}_membership_state") or "primary",
                    "voice_part_id": form.get(f"member_{member_id}_voice_part_id") or "",
                    "role_notes": form.get(f"member_{member_id}_role_notes") or "",
                }
            )
    members.update_quartet_members(quartet_id, assignments)
    return RedirectResponse(url=f"/quartets?members_saved={quartet_id}", status_code=303)


@app.post("/quartets/{quartet_id}/members/add")
async def add_quartet_member(request: Request, quartet_id: int):
    require_quartet_manager(request, quartet_id)
    if not members.quartet_detail(quartet_id):
        raise HTTPException(status_code=404, detail="Quartet not found.")
    form = await request.form()
    member_id = (form.get("member_id") or "").strip()
    if not member_id:
        return RedirectResponse(url=f"/quartets?member_required={quartet_id}", status_code=303)
    members.upsert_quartet_member(
        quartet_id,
        {
            "member_id": member_id,
            "membership_state": form.get("membership_state") or "primary",
            "voice_part_id": form.get("voice_part_id") or "",
            "role_notes": form.get("role_notes") or "",
        },
    )
    return RedirectResponse(url=f"/quartets?member_added={quartet_id}", status_code=303)


@app.post("/quartets/{quartet_id}/members/{member_id}")
async def edit_quartet_member(request: Request, quartet_id: int, member_id: int):
    require_quartet_manager(request, quartet_id)
    if not members.quartet_detail(quartet_id):
        raise HTTPException(status_code=404, detail="Quartet not found.")
    form = await request.form()
    members.upsert_quartet_member(
        quartet_id,
        {
            "member_id": str(member_id),
            "membership_state": form.get("membership_state") or "primary",
            "voice_part_id": form.get("voice_part_id") or "",
            "role_notes": form.get("role_notes") or "",
        },
    )
    return RedirectResponse(url=f"/quartets?member_saved={quartet_id}", status_code=303)


@app.post("/quartets/{quartet_id}/members/{member_id}/delete")
async def delete_quartet_member(request: Request, quartet_id: int, member_id: int):
    require_quartet_manager(request, quartet_id)
    members.delete_quartet_member(quartet_id, member_id)
    return RedirectResponse(url=f"/quartets?member_deleted={quartet_id}", status_code=303)


@app.post("/quartets/{quartet_id}/photo")
async def update_quartet_photo(request: Request, quartet_id: int):
    require_quartet_manager(request, quartet_id)
    quartet = members.quartet_detail(quartet_id)
    if not quartet:
        raise HTTPException(status_code=404, detail="Quartet not found.")
    form = await request.form()
    if form.get("remove_photo"):
        members.update_quartet_picture_path(quartet_id, "")
        return RedirectResponse(url=f"/quartets?photo_removed={quartet_id}", status_code=303)
    upload = uploaded_photo(form, "photo_upload")
    if upload:
        picture_path = photos.save_quartet_upload(upload.file, f"quartet-{quartet_id}-{quartet['name']}")
        members.update_quartet_picture_path(quartet_id, picture_path)
    return RedirectResponse(url=f"/quartets?photo_saved={quartet_id}", status_code=303)


@app.post("/quartets/{quartet_id}/delete")
async def delete_quartet(request: Request, quartet_id: int):
    require_admin(request)
    form = await request.form()
    if form.get("confirm_delete") == "1":
        members.delete_quartet(quartet_id)
    return RedirectResponse(url="/quartets?deleted=1", status_code=303)


@app.get("/members/{member_id}", response_class=HTMLResponse)
def member_detail(request: Request, member_id: int):
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    user = current_user(request)
    return templates.TemplateResponse(
        request,
        "member_detail.html",
        view_context(request, member=member, family_relationships=members.FAMILY_RELATIONSHIPS, can_edit_member=can_edit_member(user, member_id)),
    )


@app.get("/members/{member_id}/edit", response_class=HTMLResponse)
def edit_member_form(request: Request, member_id: int):
    require_member_editor(request, member_id)
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    return templates.TemplateResponse(
        request,
        "member_edit.html",
        view_context(
            request,
            member=member,
            statuses=members.statuses(),
            voice_parts=members.voice_parts(),
            quartets=members.quartets(),
            roles=members.member_roles(),
            photo_choices=photos.photo_choices(members.assigned_picture_paths(), member.get("picture_path")),
        ),
    )


@app.post("/members/{member_id}/edit")
async def update_member(request: Request, member_id: int):
    require_member_editor(request, member_id)
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    form = await request.form()
    first_name = (form.get("first_name") or "").strip()
    last_name = (form.get("last_name") or "").strip()
    if not first_name or not last_name:
        return RedirectResponse(url=f"/members/{member_id}/edit?name_required=1", status_code=303)
    members.update_member(member_id, {key: str(form.get(key) or "") for key in form.keys()})
    voice_part_ids = [int(value) for value in form.getlist("voice_part_ids") if str(value).isdigit()]
    members.update_member_voice_parts(member_id, voice_part_ids)

    selected_quartet_ids = {str(value) for value in form.getlist("quartet_ids")}
    quartet_assignments = []
    for quartet in members.quartets():
        quartet_id = str(quartet["id"])
        members.update_quartet_catalog(
            quartet["id"],
            {
                "is_active": form.get(f"quartet_{quartet_id}_is_active") or "",
                "formation_date": form.get(f"quartet_{quartet_id}_formation_date") or "",
                "deactivation_date": form.get(f"quartet_{quartet_id}_deactivation_date") or "",
                "notes": form.get(f"quartet_{quartet_id}_notes") or "",
            },
        )
        if quartet_id in selected_quartet_ids:
            quartet_assignments.append(
                {
                    "quartet_id": quartet_id,
                    "membership_state": form.get(f"quartet_{quartet_id}_membership_state") or "primary",
                    "role_notes": form.get(f"quartet_{quartet_id}_role_notes") or "",
                }
            )
    members.update_member_quartets(member_id, quartet_assignments)

    role_assignments = []
    selected_role_ids = {str(value) for value in form.getlist("role_ids")}
    for role in members.member_roles():
        role_id = str(role["id"])
        if role_id in selected_role_ids:
            role_assignments.append(
                {
                    "role_id": role_id,
                    "start_date": form.get(f"role_{role_id}_start_date") or "",
                    "end_date": form.get(f"role_{role_id}_end_date") or "",
                    "source_system": form.get(f"role_{role_id}_source_system") or "Manual",
                    "notes": form.get(f"role_{role_id}_notes") or "",
                }
            )
    for key in form.getlist("new_role_keys"):
        role_name = (form.get(f"new_role_{key}_name") or "").strip()
        if role_name:
            role_assignments.append(
                {
                    "role_name": role_name,
                    "start_date": form.get(f"new_role_{key}_start_date") or "",
                    "end_date": form.get(f"new_role_{key}_end_date") or "",
                    "source_system": "Manual",
                    "notes": form.get(f"new_role_{key}_notes") or "",
                }
            )
    members.update_member_role_assignments(member_id, role_assignments)

    email_rows = []
    for key in form.getlist("email_row_keys"):
        email_rows.append(
            {
                "email_address": form.get(f"email_{key}_email_address") or "",
                "label": form.get(f"email_{key}_label") or "",
                "is_primary": form.get(f"email_{key}_is_primary") or "",
            }
        )
    members.update_member_emails(member_id, email_rows)

    phone_rows = []
    for key in form.getlist("phone_row_keys"):
        phone_rows.append(
            {
                "phone_number": form.get(f"phone_{key}_phone_number") or "",
                "phone_type": form.get(f"phone_{key}_phone_type") or "",
                "label": form.get(f"phone_{key}_label") or "",
                "is_primary": form.get(f"phone_{key}_is_primary") or "",
            }
        )
    members.update_member_phones(member_id, phone_rows)

    address_rows = []
    for key in form.getlist("address_row_keys"):
        address_rows.append(
            {
                "address_type": form.get(f"address_{key}_address_type") or "",
                "street": form.get(f"address_{key}_street") or "",
                "city": form.get(f"address_{key}_city") or "",
                "state": form.get(f"address_{key}_state") or "",
                "postal_code": form.get(f"address_{key}_postal_code") or "",
                "country": form.get(f"address_{key}_country") or "",
                "raw_address": form.get(f"address_{key}_raw_address") or "",
                "is_primary": form.get(f"address_{key}_is_primary") or "",
            }
        )
    members.update_member_addresses(member_id, address_rows)
    return RedirectResponse(url=f"/members/{member_id}?saved=1", status_code=303)


@app.post("/members/{member_id}/family")
async def add_member_family(request: Request, member_id: int):
    require_member_editor(request, member_id)
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    form = await request.form()
    first_name = (form.get("first_name") or "").strip()
    if not first_name:
        return RedirectResponse(url=f"/members/{member_id}?family_required=1", status_code=303)
    members.add_family_member(
        member_id=member_id,
        first_name=first_name,
        last_name=form.get("last_name") or "",
        relationship=form.get("relationship") or "other",
        date_of_birth=form.get("date_of_birth") or "",
        email_address=form.get("email_address") or "",
        picture_path=form.get("picture_path") or "",
        notes=form.get("notes") or "",
    )
    return RedirectResponse(url=f"/members/{member_id}?family_added=1", status_code=303)


@app.get("/members/{member_id}/family/{family_id}/edit", response_class=HTMLResponse)
def edit_member_family_form(request: Request, member_id: int, family_id: int):
    require_member_editor(request, member_id)
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    person = members.family_member(member_id, family_id)
    if not person:
        raise HTTPException(status_code=404, detail="Family member not found.")
    return templates.TemplateResponse(
        request,
        "family_edit.html",
        view_context(
            request,
            member=member,
            person=person,
            family_relationships=members.FAMILY_RELATIONSHIPS,
            photo_choices=photos.photo_choices(members.assigned_picture_paths(), person.get("picture_path")),
        ),
    )


@app.post("/members/{member_id}/family/{family_id}/edit")
async def update_member_family(request: Request, member_id: int, family_id: int):
    require_member_editor(request, member_id)
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    person = members.family_member(member_id, family_id)
    if not person:
        raise HTTPException(status_code=404, detail="Family member not found.")
    form = await request.form()
    first_name = (form.get("first_name") or "").strip()
    if not first_name:
        return RedirectResponse(url=f"/members/{member_id}/family/{family_id}/edit?family_required=1", status_code=303)
    members.update_family_member(
        member_id=member_id,
        family_id=family_id,
        first_name=first_name,
        last_name=form.get("last_name") or "",
        relationship=form.get("relationship") or "other",
        date_of_birth=form.get("date_of_birth") or "",
        email_address=form.get("email_address") or "",
        picture_path=form.get("picture_path") or "",
        notes=form.get("notes") or "",
    )
    return RedirectResponse(url=f"/members/{member_id}?family_saved=1", status_code=303)


@app.post("/members/{member_id}/family/{family_id}/delete")
def delete_member_family(request: Request, member_id: int, family_id: int):
    require_member_editor(request, member_id)
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    members.delete_family_member(member_id, family_id)
    return RedirectResponse(url=f"/members/{member_id}?family_deleted=1", status_code=303)


def uploaded_photo(form, field_name: str) -> UploadFile | None:
    upload = form.get(field_name)
    if hasattr(upload, "filename") and upload.filename and hasattr(upload, "file"):
        return upload
    return None


@app.post("/members/{member_id}/photo")
async def update_member_photo(request: Request, member_id: int):
    require_member_editor(request, member_id)
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    form = await request.form()
    if form.get("remove_photo"):
        members.update_member_picture_path(member_id, "")
        return RedirectResponse(url=f"/members/{member_id}/edit?photo_removed=1", status_code=303)
    upload = uploaded_photo(form, "photo_upload")
    selected_photo = (form.get("selected_photo_path") or "").strip()
    picture_path = ""
    if upload:
        picture_path = photos.save_profile_upload(upload.file, "members", f"member-{member_id}")
    elif selected_photo and photos.is_assignable(selected_photo, members.assigned_picture_paths(), member.get("picture_path")):
        picture_path = selected_photo
    if picture_path:
        members.update_member_picture_path(member_id, picture_path)
    return RedirectResponse(url=f"/members/{member_id}/edit?photo_saved=1", status_code=303)


@app.post("/members/{member_id}/family/{family_id}/photo")
async def update_family_photo(request: Request, member_id: int, family_id: int):
    require_member_editor(request, member_id)
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    person = members.family_member(member_id, family_id)
    if not person:
        raise HTTPException(status_code=404, detail="Family member not found.")
    form = await request.form()
    if form.get("remove_photo"):
        members.update_family_picture_path(member_id, family_id, "")
        return RedirectResponse(url=f"/members/{member_id}/family/{family_id}/edit?photo_removed=1", status_code=303)
    upload = uploaded_photo(form, "photo_upload")
    selected_photo = (form.get("selected_photo_path") or "").strip()
    picture_path = ""
    if upload:
        picture_path = photos.save_profile_upload(upload.file, "family", f"member-{member_id}-family-{family_id}")
    elif selected_photo and photos.is_assignable(selected_photo, members.assigned_picture_paths(), person.get("picture_path")):
        picture_path = selected_photo
    if picture_path:
        members.update_family_picture_path(member_id, family_id, picture_path)
    return RedirectResponse(url=f"/members/{member_id}/family/{family_id}/edit?photo_saved=1", status_code=303)


@app.get("/photos/unassigned", response_class=HTMLResponse)
def unassigned_photos(request: Request):
    require_admin(request)
    assignments = members.photo_assignments()
    return templates.TemplateResponse(
        request,
        "unassigned_photos.html",
        view_context(request, photos=photos.roster_photos(assignments), members=members.member_options(), families=members.family_options()),
    )


@app.post("/photos/assign")
async def assign_photo(request: Request):
    require_admin(request)
    form = await request.form()
    photo_path = (form.get("photo_path") or "").strip()
    target_type = (form.get("target_type") or "").strip()
    member_id = int(form.get("member_id") or 0)
    family_id = int(form.get("family_id") or 0)
    if not photo_path:
        return RedirectResponse(url="/photos/unassigned?missing_photo=1", status_code=303)
    members.clear_picture_path(photo_path)
    if target_type == "family" and family_id:
        member_id = members.family_owner_id(family_id) or member_id
    if target_type == "family" and member_id and family_id:
        members.update_family_picture_path(member_id, family_id, photo_path)
    elif target_type == "member" and member_id:
        members.update_member_picture_path(member_id, photo_path)
    else:
        return RedirectResponse(url="/photos/unassigned?missing_target=1", status_code=303)
    return RedirectResponse(url="/photos/unassigned?assigned=1", status_code=303)


@app.post("/photos/remove")
async def remove_photo_assignment(request: Request):
    require_admin(request)
    form = await request.form()
    photo_path = (form.get("photo_path") or "").strip()
    if photo_path:
        members.clear_picture_path(photo_path)
    return RedirectResponse(url="/photos/unassigned?removed=1", status_code=303)


@app.post("/members/{member_id}/delete")
async def delete_member(request: Request, member_id: int):
    require_admin(request)
    form = await request.form()
    if form.get("confirm_delete") == "1":
        members.delete_member(member_id)
    return RedirectResponse(url="/?member_deleted=1", status_code=303)
