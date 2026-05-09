-- Canonical important dates for members and family members.

CREATE TABLE IF NOT EXISTS important_date (
    id                  SERIAL PRIMARY KEY,
    important_date      DATE NOT NULL,
    title               VARCHAR(120) NOT NULL,
    classification      VARCHAR(40) NOT NULL CHECK (classification IN (
                            'birthday',
                            'anniversary',
                            'deceased',
                            'inactive',
                            'membership_start'
                        )),
    member_id           INT REFERENCES member(id) ON DELETE CASCADE,
    family_member_id    INT REFERENCES member_family(id) ON DELETE CASCADE,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        (member_id IS NOT NULL AND family_member_id IS NULL)
        OR (member_id IS NULL AND family_member_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_important_date_member_classification
ON important_date(member_id, classification)
WHERE member_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_important_date_family_classification
ON important_date(family_member_id, classification)
WHERE family_member_id IS NOT NULL;

INSERT INTO important_date (member_id, important_date, title, classification)
SELECT id, membership_start_date, 'Membership Start', 'membership_start'
FROM member
WHERE membership_start_date IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO important_date (member_id, important_date, title, classification)
SELECT id, inactive_date, 'Inactive Date', 'inactive'
FROM member
WHERE inactive_date IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO important_date (member_id, important_date, title, classification)
SELECT id, date_of_birth, 'Birthday', 'birthday'
FROM member
WHERE date_of_birth IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO important_date (member_id, important_date, title, classification)
SELECT id, date_of_death, 'Date of Death', 'deceased'
FROM member
WHERE date_of_death IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO important_date (member_id, important_date, title, classification)
SELECT id, anniversary_date, 'Anniversary', 'anniversary'
FROM member
WHERE anniversary_date IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO important_date (family_member_id, important_date, title, classification)
SELECT id, date_of_birth, 'Birthday', 'birthday'
FROM member_family
WHERE date_of_birth IS NOT NULL
ON CONFLICT DO NOTHING;
