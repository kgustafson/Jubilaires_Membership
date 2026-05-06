-- Move voice parts to a many-to-many model so members can sing multiple parts.

CREATE TABLE IF NOT EXISTS member_voice_part (
    member_id       INT NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    voice_part_id   INT NOT NULL REFERENCES voice_part(id) ON DELETE CASCADE,
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
    notes           TEXT,
    PRIMARY KEY (member_id, voice_part_id)
);

CREATE INDEX IF NOT EXISTS idx_member_voice_part_voice_part_id ON member_voice_part(voice_part_id);

INSERT INTO voice_part (part_name) VALUES
    ('Tenor'),
    ('Lead'),
    ('Baritone'),
    ('Bass'),
    ('Violinist')
ON CONFLICT DO NOTHING;

INSERT INTO member_voice_part (member_id, voice_part_id, is_primary, notes)
SELECT m.id, vp.id, true, 'Backfilled from member.voice_part_id.'
FROM member m
JOIN voice_part vp ON vp.id = m.voice_part_id
WHERE vp.part_name NOT IN ('Tenor/Baritone', 'Baritone/Tenor', 'Ten/Bari')
ON CONFLICT DO NOTHING;

INSERT INTO member_voice_part (member_id, voice_part_id, is_primary, notes)
SELECT m.id, vp.id, vp.part_name = 'Tenor', 'Backfilled from combined Tenor/Baritone voice part.'
FROM member m
JOIN voice_part old_part ON old_part.id = m.voice_part_id
JOIN voice_part vp ON vp.part_name IN ('Tenor', 'Baritone')
WHERE old_part.part_name IN ('Tenor/Baritone', 'Baritone/Tenor', 'Ten/Bari')
ON CONFLICT DO NOTHING;

UPDATE member
SET voice_part_id = NULL
WHERE voice_part_id IN (
    SELECT id
    FROM voice_part
    WHERE part_name IN ('Tenor/Baritone', 'Baritone/Tenor', 'Ten/Bari')
);

DELETE FROM voice_part
WHERE part_name IN ('Tenor/Baritone', 'Baritone/Tenor', 'Ten/Bari')
  AND NOT EXISTS (SELECT 1 FROM member WHERE member.voice_part_id = voice_part.id)
  AND NOT EXISTS (SELECT 1 FROM member_voice_part WHERE member_voice_part.voice_part_id = voice_part.id);
