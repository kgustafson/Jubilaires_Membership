from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jubilaires_membership.services import members


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
        {"member": member, "person": person, "family_relationships": members.FAMILY_RELATIONSHIPS},
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
