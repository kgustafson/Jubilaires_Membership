-- Add one-to-many family records for members.

CREATE TABLE IF NOT EXISTS member_family (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100),
    relationship    VARCHAR(40) NOT NULL CHECK (relationship IN (
                        'spouse','partner','son','daughter','brother','sister',
                        'father','mother','child','parent','family','other'
                    )),
    email_address   VARCHAR(254),
    picture_path    TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_member_family_member_id ON member_family(member_id);

INSERT INTO member_family (member_id, first_name, last_name, relationship, notes)
SELECT
    m.id,
    split_part(trim(m.spouse_partner_name), ' ', 1) AS first_name,
    nullif(regexp_replace(trim(m.spouse_partner_name), '^\S+\s*', ''), '') AS last_name,
    'spouse',
    'Backfilled from member.spouse_partner_name; audit relationship during roster cleanup.'
FROM member m
WHERE nullif(trim(m.spouse_partner_name), '') IS NOT NULL
  AND lower(trim(m.spouse_partner_name)) NOT IN ('same', 'home')
  AND NOT EXISTS (
      SELECT 1
      FROM member_family mf
      WHERE mf.member_id = m.id
  );
