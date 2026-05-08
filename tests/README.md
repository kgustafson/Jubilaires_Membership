# Smoke Tests

These tests lightly exercise the Jubilaires Membership web app from the outside using `pytest` and `httpx`.

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

Run them while the app and database are running:

```bash
pytest tests
```

Environment overrides:

- `JUBILAIRES_SMOKE_BASE_URL`: app URL, defaults to `http://127.0.0.1:8091`
- `JUBILAIRES_SMOKE_ADMIN_USER_ID`: admin user id for the signed test session, defaults to `1`
- `JUBILAIRES_SMOKE_MEMBER_ID`: member id to use for member detail/edit checks, defaults to `27`
- `JUBILAIRES_SESSION_SECRET`: session signing secret, defaults to the local dev secret
- `JUBILAIRES_RUN_BACKUP_SMOKE=1`: also exercise the database backup POST; omitted by default to avoid creating backup files during every smoke run
