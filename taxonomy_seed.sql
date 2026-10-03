-- =====================================================================
-- UA-7 (Yajat's lead share) — Skill taxonomy seed
-- Schema reference: docs/CONTRACTS.md section 7.2
--
-- Design notes:
--   * 20 canonical skills across Foundations / Databases / Web / DevOps /
--     Data-AI, chosen so a believable target role + role_skill_requirement
--     set can be built on top for compute_gap() testing (see fixtures).
--   * Prerequisite graph is intentionally layered (Foundations -> mid ->
--     advanced) so it is acyclic by construction. Verified by hand below
--     (section "Acyclicity check").
--   * Inserts reference skills by skill_name (not hardcoded skill_id),
--     specifically so this file can be run alongside Vansh's and
--     Hemanth's UA-7 shares without id collisions — everyone's seed
--     script is safe to run in any order, any number of times.
--   * "Level" does not live on the skill table itself (per 7.2) — it only
--     exists per student (skill vector, 7.1) or per role requirement
--     (role_skill_requirement.required_level). The tier noted in each
--     comment below is just this file's internal design note for picking
--     sensible required_level values in the sample role at the bottom.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. Skills (20 total)
-- ---------------------------------------------------------------------
INSERT INTO skill (skill_name, category, created_at) VALUES
  ('Programming Fundamentals',        'Foundations', now()),  -- tier: beginner
  ('Data Structures',                 'Foundations', now()),  -- tier: intermediate
  ('Algorithms',                      'Foundations', now()),  -- tier: intermediate
  ('Python',                          'Languages',   now()),  -- tier: beginner
  ('SQL Basics',                      'Databases',   now()),  -- tier: beginner
  ('Relational Database Design',      'Databases',   now()),  -- tier: intermediate
  ('Git & Version Control',           'Tooling',     now()),  -- tier: beginner
  ('HTTP & Web Fundamentals',         'Web',         now()),  -- tier: beginner
  ('REST API Design',                 'Web',         now()),  -- tier: intermediate
  ('Backend Framework (Flask/FastAPI)','Web',        now()),  -- tier: intermediate
  ('Authentication & Authorization',  'Security',    now()),  -- tier: intermediate
  ('Unit Testing',                    'Quality',     now()),  -- tier: beginner
  ('CI/CD Fundamentals',              'DevOps',      now()),  -- tier: intermediate
  ('Docker & Containerization',       'DevOps',      now()),  -- tier: intermediate
  ('Cloud Deployment Basics',         'DevOps',      now()),  -- tier: advanced
  ('System Design Fundamentals',      'Architecture',now()),  -- tier: advanced
  ('Vector Databases',                'Data/AI',     now()),  -- tier: intermediate
  ('Knowledge Graphs',                'Data/AI',     now()),  -- tier: intermediate
  ('Machine Learning Fundamentals',   'Data/AI',     now()),  -- tier: intermediate
  ('Retrieval-Augmented Generation (RAG)', 'Data/AI', now())  -- tier: advanced
ON CONFLICT (skill_name) DO NOTHING;

-- ---------------------------------------------------------------------
-- 2. Aliases (lowercased, trimmed — per 7.2 alias matching rule)
-- ---------------------------------------------------------------------
INSERT INTO skill_alias (skill_id, alias_text)
SELECT skill_id, alias FROM skill
JOIN (VALUES
  ('Python',                            'py'),
  ('Python',                            'python3'),
  ('SQL Basics',                        'sql'),
  ('Relational Database Design',        'rdbms design'),
  ('Git & Version Control',             'git'),
  ('HTTP & Web Fundamentals',           'http'),
  ('REST API Design',                   'rest apis'),
  ('Backend Framework (Flask/FastAPI)', 'flask'),
  ('Backend Framework (Flask/FastAPI)', 'fastapi'),
  ('Authentication & Authorization',    'auth'),
  ('Unit Testing',                      'pytest'),
  ('CI/CD Fundamentals',                'ci/cd'),
  ('Docker & Containerization',         'docker'),
  ('Vector Databases',                  'vector db'),
  ('Vector Databases',                  'chromadb'),
  ('Knowledge Graphs',                  'graph db'),
  ('Knowledge Graphs',                  'neo4j'),
  ('Machine Learning Fundamentals',     'ml'),
  ('Retrieval-Augmented Generation (RAG)', 'rag')
) AS aliases(skill_name, alias) ON skill.skill_name = aliases.skill_name
ON CONFLICT (alias_text) DO NOTHING;

-- ---------------------------------------------------------------------
-- 3. Prerequisite edges (skill_id requires prerequisite_skill_id)
-- ---------------------------------------------------------------------
INSERT INTO skill_prerequisite (skill_id, prerequisite_skill_id)
SELECT s.skill_id, p.skill_id FROM
(VALUES
  ('Data Structures',                 'Programming Fundamentals'),
  ('Algorithms',                      'Data Structures'),
  ('Python',                          'Programming Fundamentals'),
  ('Relational Database Design',      'SQL Basics'),
  ('REST API Design',                 'HTTP & Web Fundamentals'),
  ('REST API Design',                 'Python'),
  ('Backend Framework (Flask/FastAPI)','REST API Design'),
  ('Authentication & Authorization',  'REST API Design'),
  ('Unit Testing',                    'Programming Fundamentals'),
  ('CI/CD Fundamentals',              'Git & Version Control'),
  ('CI/CD Fundamentals',              'Unit Testing'),
  ('Docker & Containerization',       'CI/CD Fundamentals'),
  ('Cloud Deployment Basics',         'Docker & Containerization'),
  ('System Design Fundamentals',      'Data Structures'),
  ('System Design Fundamentals',      'REST API Design'),
  ('Vector Databases',                'Relational Database Design'),
  ('Knowledge Graphs',                'Relational Database Design'),
  ('Machine Learning Fundamentals',   'Algorithms'),
  ('Machine Learning Fundamentals',   'Python'),
  ('Retrieval-Augmented Generation (RAG)', 'Vector Databases'),
  ('Retrieval-Augmented Generation (RAG)', 'Machine Learning Fundamentals')
) AS edges(skill_name, prereq_name)
JOIN skill s ON s.skill_name = edges.skill_name
JOIN skill p ON p.skill_name = edges.prereq_name
ON CONFLICT (skill_id, prerequisite_skill_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- 4. Sample career role + requirements, for compute_gap() fixtures
--    and for Sprint 2/3 end-to-end demo data.
-- ---------------------------------------------------------------------
INSERT INTO career_role (role_name, description) VALUES
  ('Backend Developer', 'Entry-level backend engineering role used as the demo target role for M2 gap analysis.')
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO role_skill_requirement (role_id, skill_id, required_level, weight)
SELECT r.role_id, s.skill_id, req.required_level, req.weight FROM
(VALUES
  ('Python',                           'intermediate', 5),
  ('REST API Design',                  'intermediate', 4),
  ('SQL Basics',                       'beginner',     3),
  ('Docker & Containerization',        'beginner',     2),
  ('Unit Testing',                     'beginner',     1)
) AS req(skill_name, required_level, weight)
JOIN skill s ON s.skill_name = req.skill_name
CROSS JOIN career_role r WHERE r.role_name = 'Backend Developer'
ON CONFLICT (role_id, skill_id) DO NOTHING;

COMMIT;

-- =====================================================================
-- Acyclicity check (manual, for the record — satisfies the "done when"
-- criterion in the kickoff plan: "valid acyclic prerequisite graph")
--
-- The edges above form three strictly increasing tiers with no back
-- edges:
--   Tier 0 (no prerequisites): Programming Fundamentals, SQL Basics,
--     Git & Version Control, HTTP & Web Fundamentals
--   Tier 1 (depends only on Tier 0): Data Structures, Python,
--     Relational Database Design, Unit Testing
--   Tier 2 (depends only on Tier 0/1): Algorithms, REST API Design,
--     CI/CD Fundamentals, Vector Databases, Knowledge Graphs
--   Tier 3 (depends only on Tier 0/1/2): Backend Framework,
--     Authentication & Authorization, Docker & Containerization,
--     System Design Fundamentals, Machine Learning Fundamentals
--   Tier 4 (depends only on Tier 0-3): Cloud Deployment Basics,
--     Retrieval-Augmented Generation (RAG)
--
-- Every edge points from a higher tier to a strictly lower tier, so no
-- cycle is possible. Combined with Vansh's and Hemanth's shares this
-- should clear the ≥30-skill Sprint 1 target; flag in standup if the
-- running total is short by Fri 9 Oct per risk #1.
-- =====================================================================
