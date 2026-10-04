-- UA-7: Hemanth's five canonical skills for progress testing.
-- Uses the shared taxonomy_seed.sql INSERT format from main.
-- Requires the shared skill table; does not create or alter schema.
-- Skill names are distinct from Yajat's existing twenty skills.
BEGIN;

INSERT INTO skill (skill_name, category, created_at) VALUES
  ('Software Testing Fundamentals', 'Quality', now()),
  ('Integration Testing', 'Quality', now()),
  ('API Testing', 'Quality', now()),
  ('Test Automation', 'Quality', now()),
  ('Code Coverage Analysis', 'Quality', now())
ON CONFLICT (skill_name) DO NOTHING;

COMMIT;
