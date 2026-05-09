-- =============================================================================
-- JUBILAIRES MEMBERSHIP DATABASE SCHEMA
-- Starter PostgreSQL schema for the 2026 chapter membership roster.
-- =============================================================================

CREATE TABLE membership_status (
    id              SERIAL PRIMARY KEY,
    status_code     VARCHAR(40) NOT NULL UNIQUE,
    description     TEXT
);

CREATE TABLE voice_part (
    id              SERIAL PRIMARY KEY,
    part_name       VARCHAR(40) NOT NULL UNIQUE
);

CREATE TABLE quartet (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120) NOT NULL UNIQUE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    formation_date  DATE,
    deactivation_date DATE,
    picture_path    TEXT,
    notes           TEXT
);

CREATE TABLE member (
    id                  SERIAL PRIMARY KEY,
    last_name           VARCHAR(100) NOT NULL,
    first_name          VARCHAR(100) NOT NULL,
    preferred_name      VARCHAR(100),
    spouse_partner_name VARCHAR(150),
    voice_part_id       INT REFERENCES voice_part(id),
    status_id           INT REFERENCES membership_status(id),
    membership_start_date DATE,
    inactive_date      DATE,
    date_of_birth      DATE,
    date_of_death      DATE,
    anniversary_date   DATE,
    picture_path       TEXT,
    notes               TEXT,
    source_document     TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (last_name, first_name)
);

CREATE TABLE member_voice_part (
    member_id       INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    voice_part_id   INT NOT NULL REFERENCES voice_part(id) ON DELETE CASCADE,
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
    notes           TEXT,
    PRIMARY KEY (member_id, voice_part_id)
);

CREATE TABLE member_phone (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    phone_type      VARCHAR(20), -- H, C, O, F, other
    phone_number    VARCHAR(40) NOT NULL,
    label           VARCHAR(80),
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE member_email (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    email_address   VARCHAR(254) NOT NULL,
    label           VARCHAR(80),
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE member_family (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100),
    relationship    VARCHAR(40) NOT NULL CHECK (relationship IN (
                        'spouse','partner','son','daughter','brother','sister',
                        'father','mother','child','parent','family','other'
    )),
    date_of_birth  DATE,
    email_address   VARCHAR(254),
    phone_number    VARCHAR(40),
    picture_path    TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE member_address (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    address_type    VARCHAR(40) NOT NULL DEFAULT 'primary',
    street          TEXT,
    city            VARCHAR(100),
    state           VARCHAR(30),
    postal_code     VARCHAR(20),
    country         VARCHAR(80) NOT NULL DEFAULT 'USA',
    raw_address     TEXT,
    is_primary      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE member_quartet (
    member_id       INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    quartet_id      INT NOT NULL REFERENCES quartet(id) ON DELETE CASCADE,
    membership_state VARCHAR(20) NOT NULL DEFAULT 'primary' CHECK (membership_state IN ('primary', 'alternate')),
    voice_part_id   INT REFERENCES voice_part(id),
    role_notes      TEXT,
    PRIMARY KEY (member_id, quartet_id)
);

CREATE TABLE member_classification (
    id                  SERIAL PRIMARY KEY,
    classification_type VARCHAR(40) NOT NULL CHECK (classification_type IN ('role', 'subgroup', 'label')),
    name                VARCHAR(160) NOT NULL,
    source_system       VARCHAR(80) NOT NULL DEFAULT 'Choir Genius',
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (classification_type, name, source_system)
);

CREATE TABLE member_classification_assignment (
    member_id           INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    classification_id   INT NOT NULL REFERENCES member_classification(id) ON DELETE CASCADE,
    source_value        TEXT,
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (member_id, classification_id)
);

CREATE TABLE member_external_account (
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

CREATE TABLE member_emergency_contact (
    id                  SERIAL PRIMARY KEY,
    member_id           INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    contact_name        VARCHAR(160),
    relationship        VARCHAR(80),
    phone_number        VARCHAR(80),
    raw_contact         TEXT NOT NULL,
    source_system       VARCHAR(80) NOT NULL DEFAULT 'Choir Genius',
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE member_role (
    id                  SERIAL PRIMARY KEY,
    role_name           VARCHAR(160) NOT NULL UNIQUE,
    description         TEXT
);

CREATE TABLE member_role_assignment (
    id                  SERIAL PRIMARY KEY,
    member_id           INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    role_id             INT NOT NULL REFERENCES member_role(id) ON DELETE CASCADE,
    start_date          DATE,
    end_date            DATE,
    source_system       VARCHAR(80),
    notes               TEXT,
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE important_date (
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

CREATE UNIQUE INDEX idx_important_date_member_classification
ON important_date(member_id, classification)
WHERE member_id IS NOT NULL;

CREATE UNIQUE INDEX idx_important_date_family_classification
ON important_date(family_member_id, classification)
WHERE family_member_id IS NOT NULL;

CREATE TABLE roster_source (
    id              SERIAL PRIMARY KEY,
    source_name     VARCHAR(200) NOT NULL,
    source_path     TEXT NOT NULL,
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes           TEXT
);

INSERT INTO membership_status (status_code, description) VALUES
    ('active', 'Active member'),
    ('inactive', 'Inactive member'),
    ('dual', 'Dual chapter member'),
    ('former', 'Former member')
ON CONFLICT DO NOTHING;

INSERT INTO voice_part (part_name) VALUES
    ('Tenor'),
    ('Lead'),
    ('Baritone'),
    ('Bass'),
    ('Violinist')
ON CONFLICT DO NOTHING;
