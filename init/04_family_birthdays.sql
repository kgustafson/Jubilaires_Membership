-- Move family birthdays onto member_family rows.

ALTER TABLE member_family
    ADD COLUMN IF NOT EXISTS birthday_month SMALLINT CHECK (birthday_month BETWEEN 1 AND 12),
    ADD COLUMN IF NOT EXISTS birthday_day SMALLINT CHECK (birthday_day BETWEEN 1 AND 31);

UPDATE member_family mf
SET
    birthday_month = m.spouse_birthday_month,
    birthday_day = m.spouse_birthday_day,
    notes = concat_ws(
        E'\n',
        nullif(mf.notes, ''),
        'Birthday backfilled from legacy member spouse_birthday fields.'
    )
FROM member m
WHERE mf.member_id = m.id
  AND mf.relationship IN ('spouse', 'partner')
  AND m.spouse_birthday_month IS NOT NULL
  AND m.spouse_birthday_day IS NOT NULL
  AND mf.birthday_month IS NULL
  AND mf.birthday_day IS NULL;
