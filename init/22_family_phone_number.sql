-- Family member phone contact.

ALTER TABLE member_family
ADD COLUMN IF NOT EXISTS phone_number VARCHAR(40);
