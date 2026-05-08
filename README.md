# Jubilaires Membership

Jubilaires Barbershop Group membership database with a FastAPI/Jinja web front end.

This project is operationally separate from all other projects. It should use its own virtual environment, Docker services, database, ports, secrets, backups, media storage, deployment pipeline, and production hosting resources.

## Stack

- PostgreSQL 16 in Docker
- FastAPI
- Jinja2 templates
- SQLAlchemy
- Adminer for direct database inspection

## Environment

Copy `.env.example` to `.env` before production deployment and replace the placeholder secrets:

```bash
cp .env.example .env
```

`.env` is intentionally ignored by Git.

## Start the full Docker stack

```bash
docker compose up -d --build
```

The containerized web app will be available at http://127.0.0.1:8092.
Adminer will be available at http://127.0.0.1:8081.

Persistent host directories are mounted into the app container:

- `jubilaires_membership/static/photos` for member, family, roster, and quartet photos.
- `backups` for database backup files.

## Start the production Docker stack

The production compose file runs PostgreSQL, the app, and a Caddy reverse proxy. It does not run Adminer or publish PostgreSQL to the host.

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Caddy serves the app through the domain configured as `JUBILAIRES_DOMAIN` in `.env`.

## Separation Requirements

- Do not reuse another project's Python virtual environment.
- Do not reuse another project's database, Docker volumes, credentials, ports, media folders, backup jobs, or deployment resources.
- Keep all Jubilaires code, imports, static assets, extracted photos, and operational scripts under this project directory.
- Use `JUBILAIRES_DATABASE_URL` for database overrides.

## Start the database only

```bash
docker compose up -d db adminer
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
