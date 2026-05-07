-- Application user accounts and approval workflow.

CREATE TABLE IF NOT EXISTS app_user (
    id                  SERIAL PRIMARY KEY,
    member_id           INT REFERENCES member(id) ON DELETE SET NULL,
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    email               VARCHAR(254) NOT NULL UNIQUE,
    username            VARCHAR(80) NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    role                VARCHAR(40) CHECK (role IN ('member', 'administrator')),
    last_login_at       TIMESTAMPTZ,
    approved_at         TIMESTAMPTZ,
    approved_by_user_id INT REFERENCES app_user(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_user_member_id ON app_user(member_id);
CREATE INDEX IF NOT EXISTS idx_app_user_pending ON app_user(created_at) WHERE role IS NULL;
