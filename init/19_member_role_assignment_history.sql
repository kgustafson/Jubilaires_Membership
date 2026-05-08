DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'member_role_assignment'
          AND column_name = 'id'
    ) THEN
        ALTER TABLE member_role_assignment ADD COLUMN id SERIAL;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'member_role_assignment_pkey'
          AND conrelid = 'member_role_assignment'::regclass
    ) THEN
        ALTER TABLE member_role_assignment DROP CONSTRAINT member_role_assignment_pkey;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'member_role_assignment_id_pkey'
          AND conrelid = 'member_role_assignment'::regclass
    ) THEN
        ALTER TABLE member_role_assignment
            ADD CONSTRAINT member_role_assignment_id_pkey PRIMARY KEY (id);
    END IF;
END $$;
