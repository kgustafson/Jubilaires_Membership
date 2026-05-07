-- Mark Choir Genius applicants and former subgroup members inactive.

WITH inactive_status AS (
    SELECT id
    FROM membership_status
    WHERE status_code = 'inactive'
),
classified_members AS (
    SELECT DISTINCT m.id
    FROM member m
    JOIN member_classification_assignment mca ON mca.member_id = m.id
    JOIN member_classification mc ON mc.id = mca.classification_id
    WHERE (mc.classification_type = 'role' AND mc.name = 'Applicant')
       OR (mc.classification_type = 'subgroup' AND mc.name = 'Former')
)
UPDATE member m
SET status_id = inactive_status.id,
    inactive_date = COALESCE(m.inactive_date, CURRENT_DATE),
    updated_at = now()
FROM inactive_status, classified_members
WHERE m.id = classified_members.id;
