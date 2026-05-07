-- =============================================================================
-- Choir Genius account metadata, emergency contacts, and leadership roles.
-- =============================================================================

CREATE TABLE IF NOT EXISTS member_external_account (
    member_id           INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    source_system       VARCHAR(80) NOT NULL DEFAULT 'Choir Genius',
    username            VARCHAR(160),
    qr_code             VARCHAR(80),
    user_id             VARCHAR(80),
    member_number       VARCHAR(80),
    source_status       VARCHAR(80),
    contact_pref        VARCHAR(80),
    email_pref          VARCHAR(80),
    company_name        VARCHAR(160),
    url                 TEXT,
    parents             TEXT,
    parent_emails       TEXT,
    private_notes       TEXT,
    skills              TEXT,
    dues_paid_until     DATE,
    height_text         VARCHAR(40),
    raw_payload         JSONB,
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (member_id, source_system)
);

CREATE TABLE IF NOT EXISTS member_emergency_contact (
    id                  SERIAL PRIMARY KEY,
    member_id           INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    contact_name        VARCHAR(160),
    relationship        VARCHAR(80),
    phone_number        VARCHAR(80),
    raw_contact         TEXT NOT NULL,
    source_system       VARCHAR(80) NOT NULL DEFAULT 'Choir Genius',
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS member_role (
    id                  SERIAL PRIMARY KEY,
    role_name           VARCHAR(160) NOT NULL UNIQUE,
    description         TEXT
);

CREATE TABLE IF NOT EXISTS member_role_assignment (
    member_id           INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    role_id             INT NOT NULL REFERENCES member_role(id) ON DELETE CASCADE,
    start_date          DATE,
    end_date            DATE,
    source_system       VARCHAR(80),
    notes               TEXT,
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (member_id, role_id, source_system)
);
