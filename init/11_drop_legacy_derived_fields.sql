-- Remove legacy fields that are now derived from explicit date records.

ALTER TABLE member
    DROP COLUMN IF EXISTS years_with_group,
    DROP COLUMN IF EXISTS birthday_month,
    DROP COLUMN IF EXISTS birthday_day,
    DROP COLUMN IF EXISTS spouse_birthday_month,
    DROP COLUMN IF EXISTS spouse_birthday_day;

ALTER TABLE member_family
    DROP COLUMN IF EXISTS birthday_month,
    DROP COLUMN IF EXISTS birthday_day;
