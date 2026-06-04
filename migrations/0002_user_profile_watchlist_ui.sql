-- UI/auth/profile support for migrated prototype flows.
ALTER TABLE users ADD COLUMN first_name TEXT;
ALTER TABLE users ADD COLUMN last_name TEXT;
ALTER TABLE users ADD COLUMN onboarding_json TEXT;
