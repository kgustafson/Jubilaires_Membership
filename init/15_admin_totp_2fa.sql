-- Add TOTP two-factor authentication and hashed recovery codes.

ALTER TABLE app_user
ADD COLUMN IF NOT EXISTS totp_secret TEXT,
ADD COLUMN IF NOT EXISTS totp_enabled_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS app_user_recovery_code (
    id              SERIAL PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    code_hash       TEXT NOT NULL,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_user_recovery_code_user_id
ON app_user_recovery_code(user_id);
