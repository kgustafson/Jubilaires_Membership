-- =============================================================================
-- Quartet lifecycle tracking.
-- =============================================================================

ALTER TABLE quartet
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS formation_date DATE,
    ADD COLUMN IF NOT EXISTS deactivation_date DATE;
