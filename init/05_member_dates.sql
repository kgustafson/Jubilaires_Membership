-- Promote loose roster year/month fields into explicit date fields.

ALTER TABLE member
    ADD COLUMN IF NOT EXISTS membership_start_date DATE,
    ADD COLUMN IF NOT EXISTS inactive_date DATE,
    ADD COLUMN IF NOT EXISTS date_of_birth DATE,
    ADD COLUMN IF NOT EXISTS date_of_death DATE,
    ADD COLUMN IF NOT EXISTS anniversary_date DATE;

ALTER TABLE member_family
    ADD COLUMN IF NOT EXISTS date_of_birth DATE;

UPDATE member
SET membership_start_date = make_date(2025 - years_with_group, 1, 1)
WHERE years_with_group IS NOT NULL
  AND membership_start_date IS NULL;
