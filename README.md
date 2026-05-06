# Jubilaires Membership

Jubilaires Barbershop Group membership database with a FastAPI/Jinja web front end.

This project is operationally separate from all other projects. It should use its own virtual environment, Docker services, database, ports, secrets, backups, media storage, deployment pipeline, and AWS resources.

## Stack

- PostgreSQL 16 in Docker
- FastAPI
- Jinja2 templates
- SQLAlchemy
- Adminer for direct database inspection

## Separation Requirements

- Do not reuse another project's Python virtual environment.
- Do not reuse another project's database, Docker volumes, credentials, ports, media folders, backup jobs, or deployment resources.
- Keep all Jubilaires code, imports, static assets, extracted photos, and operational scripts under this project directory.
- Use `JUBILAIRES_DATABASE_URL` for database overrides.

## Start the database

```bash
docker compose up -d
```

Adminer will be available at http://localhost:8081.

Connection settings:

- System: PostgreSQL
- Server: db
- Username: admin
- Password: jubilaires
- Database: jubilaires_membership

## Run the web app

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python -m uvicorn jubilaires_membership.app:app --reload --host 127.0.0.1 --port 8091
```

The web app will be available at http://127.0.0.1:8091.

## Import the 2026 roster

After the database is running and dependencies are installed:

```bash
python scripts/import_chapter_membership.py
```

The importer reads the DOCX with `textutil`, loads the fields it can identify, and stores each member's source text in `member.notes` so the records can be audited.

## Source document

The current membership roster lives at:

```text
/Users/kurtgustafson/Downloads/ChapterMembership2026.docx
```

The database schema is designed around the fields visible in that file: member, spouse/partner, part, years, birthdays, anniversary, phones, address, email, quartets, and status.
