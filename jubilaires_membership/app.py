from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jubilaires_membership.services import members, photos


app = FastAPI(title="Jubilaires Membership")
APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parent
app.mount("/static", StaticFiles(directory=str(APP_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))


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
        {
            "counts": members.dashboard_counts(),
            "members": members.member_rows(),
            "app_version": application_version(),
        },
    )


@app.get("/members/{member_id}", response_class=HTMLResponse)
def member_detail(request: Request, member_id: int):
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    return templates.TemplateResponse(
        request,
        "member_detail.html",
        {"member": member, "family_relationships": members.FAMILY_RELATIONSHIPS},
    )


@app.get("/members/{member_id}/edit", response_class=HTMLResponse)
def edit_member_form(request: Request, member_id: int):
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    return templates.TemplateResponse(
        request,
        "member_edit.html",
        {
            "member": member,
            "statuses": members.statuses(),
            "voice_parts": members.voice_parts(),
            "quartets": members.quartets(),
            "roles": members.member_roles(),
            "photo_choices": photos.photo_choices(members.assigned_picture_paths(), member.get("picture_path")),
        },
    )


@app.post("/members/{member_id}/edit")
async def update_member(request: Request, member_id: int):
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
    member = members.member_detail(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    person = members.family_member(member_id, family_id)
    if not person:
        raise HTTPException(status_code=404, detail="Family member not found.")
    return templates.TemplateResponse(
        request,
        "family_edit.html",
        {
            "member": member,
            "person": person,
            "family_relationships": members.FAMILY_RELATIONSHIPS,
            "photo_choices": photos.photo_choices(members.assigned_picture_paths(), person.get("picture_path")),
        },
    )


@app.post("/members/{member_id}/family/{family_id}/edit")
async def update_member_family(request: Request, member_id: int, family_id: int):
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
def delete_member_family(member_id: int, family_id: int):
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
    assignments = members.photo_assignments()
    return templates.TemplateResponse(
        request,
        "unassigned_photos.html",
        {
            "photos": photos.roster_photos(assignments),
            "members": members.member_options(),
            "families": members.family_options(),
        },
    )


@app.post("/photos/assign")
async def assign_photo(request: Request):
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
    form = await request.form()
    photo_path = (form.get("photo_path") or "").strip()
    if photo_path:
        members.clear_picture_path(photo_path)
    return RedirectResponse(url="/photos/unassigned?removed=1", status_code=303)
