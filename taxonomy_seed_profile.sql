-- =====================================================================
-- UA-7 follow-up (Vansh, M1) — Skill taxonomy seed, part 3
-- Schema: docs/CONTRACTS.md section 2. Load after taxonomy_seed.sql.
--
-- Adds 5 language and platform skills that students commonly list on a
-- resume and that the base seed does not yet cover. Everything else this
-- file once added is now in taxonomy_seed.sql (#78), so it is not repeated
-- here: duplicate or near-duplicate skills (a second "Pandas", a second
-- "Linux") would split one skill across two canonical entries.
--
-- Same conventions as taxonomy_seed.sql: rows reference skills by name, not
-- id, and every insert is ON CONFLICT DO NOTHING, so the file can be run in
-- any order after the base seed, any number of times. Aliases are
-- lowercased and trimmed; none repeats an existing alias or skill name
-- (checked by backend/taxonomy/test_seed_data.py).
-- =====================================================================

BEGIN;

INSERT INTO skill (skill_name, category, created_at) VALUES
  ('TypeScript',  'Languages', now()),
  ('Java',        'Languages', now()),
  ('C++',         'Languages', now()),
  ('Node.js',     'Web',       now()),
  ('Kubernetes',  'DevOps',    now())
ON CONFLICT (skill_name) DO NOTHING;

INSERT INTO skill_alias (skill_id, alias_text)
SELECT skill_id, alias FROM skill
JOIN (VALUES
  ('TypeScript',  'ts'),
  ('Java',        'core java'),
  ('C++',         'cpp'),
  ('C++',         'c plus plus'),
  ('Node.js',     'node'),
  ('Node.js',     'nodejs'),
  ('Kubernetes',  'k8s')
) AS aliases(skill_name, alias) ON skill.skill_name = aliases.skill_name
ON CONFLICT (alias_text) DO NOTHING;

-- skill_id requires prerequisite_skill_id; every prerequisite is in the
-- base seed, so no cycle is possible (also checked by the seed test).
INSERT INTO skill_prerequisite (skill_id, prerequisite_skill_id)
SELECT s.skill_id, p.skill_id FROM
(VALUES
  ('TypeScript',  'JavaScript'),
  ('Java',        'Programming Fundamentals'),
  ('C++',         'Programming Fundamentals'),
  ('Node.js',     'JavaScript'),
  ('Kubernetes',  'Docker & Containerization')
) AS edges(skill_name, prereq_name)
JOIN skill s ON s.skill_name = edges.skill_name
JOIN skill p ON p.skill_name = edges.prereq_name
ON CONFLICT (skill_id, prerequisite_skill_id) DO NOTHING;

COMMIT;
