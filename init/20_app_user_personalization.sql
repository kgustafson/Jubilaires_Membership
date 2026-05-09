-- User personalization settings.

ALTER TABLE app_user
ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(20) NOT NULL DEFAULT 'light';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'app_user_theme_preference_check'
    ) THEN
        ALTER TABLE app_user
        ADD CONSTRAINT app_user_theme_preference_check
        CHECK (theme_preference IN ('light', 'dark'));
    END IF;
END $$;
