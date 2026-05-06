-- Store a member portrait path separately from family portraits.

ALTER TABLE member
    ADD COLUMN IF NOT EXISTS picture_path TEXT;
