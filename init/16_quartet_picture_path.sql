-- Quartet group photos.

ALTER TABLE quartet
    ADD COLUMN IF NOT EXISTS picture_path TEXT;
