-- =============================================================================
-- Choir Genius / external classification support.
-- Roles, subgroups, and labels from external systems are stored separately from
-- internal leadership role history.
-- =============================================================================

CREATE TABLE IF NOT EXISTS member_classification (
    id                  SERIAL PRIMARY KEY,
    classification_type VARCHAR(40) NOT NULL CHECK (classification_type IN ('role', 'subgroup', 'label')),
    name                VARCHAR(160) NOT NULL,
    source_system       VARCHAR(80) NOT NULL DEFAULT 'Choir Genius',
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (classification_type, name, source_system)
);

CREATE TABLE IF NOT EXISTS member_classification_assignment (
    member_id           INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    classification_id   INT NOT NULL REFERENCES member_classification(id) ON DELETE CASCADE,
    source_value        TEXT,
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (member_id, classification_id)
);
