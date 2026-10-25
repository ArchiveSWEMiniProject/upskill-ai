-- =====================================================================
-- UA-7 (Vansh's share, M1) — Skill taxonomy seed, part 3
-- Schema: docs/CONTRACTS.md section 2. Load after taxonomy_seed.sql.
--
-- Adds 15 canonical skills, bringing the taxonomy to 40 (20 in
-- taxonomy_seed.sql, 5 in taxonomy_seed_progress.sql). Chosen for the
-- profile side: the frontend and language skills students most often list
-- on a resume (React is the variant example in REQ-F1-20 and TC-F1-08),
-- plus the data and DevOps skills the two target roles build towards.
--
-- Same conventions as taxonomy_seed.sql: rows reference skills by name, not
-- id, and every insert is ON CONFLICT DO NOTHING, so the file can be run in
-- any order after the base seed, any number of times. Aliases are
-- lowercased and trimmed; none repeats an existing alias or skill name.
-- =====================================================================

BEGIN;

INSERT INTO skill (skill_name, category, created_at) VALUES
  ('JavaScript',               'Languages',  now()),
  ('TypeScript',               'Languages',  now()),
  ('Java',                     'Languages',  now()),
  ('C++',                      'Languages',  now()),
  ('HTML & CSS',               'Web',        now()),
  ('React',                    'Web',        now()),
  ('Node.js',                  'Web',        now()),
  ('Next.js',                  'Web',        now()),
  ('NoSQL Databases',          'Databases',  now()),
  ('Linux & Shell Scripting',  'Tooling',    now()),
  ('Kubernetes',               'DevOps',     now()),
  ('Statistics Fundamentals',  'Data/AI',    now()),
  ('Pandas',                   'Data/AI',    now()),
  ('Data Visualization',       'Data/AI',    now()),
  ('Agile & Scrum',            'Process',    now())
ON CONFLICT (skill_name) DO NOTHING;

INSERT INTO skill_alias (skill_id, alias_text)
SELECT skill_id, alias FROM skill
JOIN (VALUES
  ('JavaScript',              'js'),
  ('JavaScript',              'ecmascript'),
  ('JavaScript',              'javascript es6'),
  ('TypeScript',              'ts'),
  ('Java',                    'core java'),
  ('C++',                     'cpp'),
  ('C++',                     'c plus plus'),
  ('HTML & CSS',              'html'),
  ('HTML & CSS',              'css'),
  ('HTML & CSS',              'html5'),
  ('HTML & CSS',              'css3'),
  ('React',                   'reactjs'),
  ('React',                   'react.js'),
  ('Node.js',                 'node'),
  ('Node.js',                 'nodejs'),
  ('Next.js',                 'nextjs'),
  ('NoSQL Databases',         'nosql'),
  ('NoSQL Databases',         'mongodb'),
  ('Linux & Shell Scripting', 'linux'),
  ('Linux & Shell Scripting', 'bash'),
  ('Linux & Shell Scripting', 'shell scripting'),
  ('Kubernetes',              'k8s'),
  ('Statistics Fundamentals', 'statistics'),
  ('Statistics Fundamentals', 'stats'),
  ('Data Visualization',      'data viz'),
  ('Data Visualization',      'matplotlib'),
  ('Agile & Scrum',           'agile'),
  ('Agile & Scrum',           'scrum')
) AS aliases(skill_name, alias) ON skill.skill_name = aliases.skill_name
ON CONFLICT (alias_text) DO NOTHING;

-- skill_id requires prerequisite_skill_id. Every edge points to a skill that
-- is either in the base seed or earlier in this chain, so no cycle is
-- possible (checked by backend/taxonomy/test_seed_data.py).
INSERT INTO skill_prerequisite (skill_id, prerequisite_skill_id)
SELECT s.skill_id, p.skill_id FROM
(VALUES
  ('JavaScript',          'Programming Fundamentals'),
  ('TypeScript',          'JavaScript'),
  ('Java',                'Programming Fundamentals'),
  ('C++',                 'Programming Fundamentals'),
  ('HTML & CSS',          'HTTP & Web Fundamentals'),
  ('React',               'JavaScript'),
  ('React',               'HTML & CSS'),
  ('Node.js',             'JavaScript'),
  ('Next.js',             'React'),
  ('Next.js',             'Node.js'),
  ('NoSQL Databases',     'SQL Basics'),
  ('Kubernetes',          'Docker & Containerization'),
  ('Pandas',              'Python'),
  ('Data Visualization',  'Pandas'),
  ('Data Visualization',  'Statistics Fundamentals')
) AS edges(skill_name, prereq_name)
JOIN skill s ON s.skill_name = edges.skill_name
JOIN skill p ON p.skill_name = edges.prereq_name
ON CONFLICT (skill_id, prerequisite_skill_id) DO NOTHING;

COMMIT;
