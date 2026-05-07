-- Track the voice part sung by a member in a specific quartet.
-- This is intentionally independent of the member's general voice part profile.

ALTER TABLE member_quartet
    ADD COLUMN IF NOT EXISTS voice_part_id INT REFERENCES voice_part(id);
