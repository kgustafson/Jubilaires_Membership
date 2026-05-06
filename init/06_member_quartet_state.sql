-- Track whether a quartet assignment is a primary member or an alternate.

ALTER TABLE member_quartet
    ADD COLUMN IF NOT EXISTS membership_state VARCHAR(20) NOT NULL DEFAULT 'primary';

ALTER TABLE member_quartet
    DROP CONSTRAINT IF EXISTS member_quartet_membership_state_check;

ALTER TABLE member_quartet
    ADD CONSTRAINT member_quartet_membership_state_check
    CHECK (membership_state IN ('primary', 'alternate'));

UPDATE member_quartet
SET membership_state = 'primary'
WHERE membership_state IS NULL;
