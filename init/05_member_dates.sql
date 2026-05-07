-- Ensure explicit member date fields exist.

ALTER TABLE member
    ADD COLUMN IF NOT EXISTS membership_start_date DATE,
    ADD COLUMN IF NOT EXISTS inactive_date DATE,
    ADD COLUMN IF NOT EXISTS date_of_birth DATE,
    ADD COLUMN IF NOT EXISTS date_of_death DATE,
    ADD COLUMN IF NOT EXISTS anniversary_date DATE;

ALTER TABLE member_family
    ADD COLUMN IF NOT EXISTS date_of_birth DATE;
