-- UA-7: Hemanth's five canonical skills for progress testing.
-- Uses the shared taxonomy_seed.sql INSERT format from main.
-- Requires the shared skill table; does not create or alter schema.
-- API Testing also exists in the shared seed; reuse its canonical row.
-- The other four skills are added only when absent.
BEGIN;

INSERT INTO skill (skill_name, category, created_at) VALUES
  ('Software Testing Fundamentals', 'Quality', now()),
  ('Integration Testing', 'Quality', now()),
  ('API Testing', 'Quality', now()),
  ('Test Automation', 'Quality', now()),
  ('Code Coverage Analysis', 'Quality', now())
ON CONFLICT (skill_name) DO NOTHING;

-- Canonical IDs are looked up, never assumed to match another developer's DB.
INSERT INTO skill_alias (skill_id, alias_text)
SELECT skill.skill_id, aliases.alias_text
FROM (VALUES
  ('Software Testing Fundamentals', 'software testing'),
  ('Integration Testing', 'integration tests'),
  ('API Testing', 'api tests'),
  ('Test Automation', 'automated testing'),
  ('Code Coverage Analysis', 'coverage analysis')
) AS aliases(skill_name, alias_text)
JOIN skill ON skill.skill_name = aliases.skill_name
ON CONFLICT (alias_text) DO NOTHING;

-- An acyclic, self-contained prerequisite contribution; no runtime M2 logic.
INSERT INTO skill_prerequisite (skill_id, prerequisite_skill_id)
SELECT target.skill_id, prerequisite.skill_id
FROM (VALUES
  ('Integration Testing', 'Software Testing Fundamentals'),
  ('API Testing', 'Integration Testing'),
  ('Test Automation', 'Software Testing Fundamentals'),
  ('Code Coverage Analysis', 'Test Automation')
) AS edges(skill_name, prerequisite_name)
JOIN skill target ON target.skill_name = edges.skill_name
JOIN skill prerequisite ON prerequisite.skill_name = edges.prerequisite_name
ON CONFLICT (skill_id, prerequisite_skill_id) DO NOTHING;

COMMIT;
