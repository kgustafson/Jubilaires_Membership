-- Track the last successful login timestamp for each application user.

ALTER TABLE app_user
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
