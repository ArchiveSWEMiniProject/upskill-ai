-- =====================================================================
-- UA-8 — Resource catalogue seed (shared; added by Vansh)
-- Schema: docs/CONTRACTS.md section 3. Load after the taxonomy seeds
-- (taxonomy_seed.sql first), e.g.:
--     psql "$DATABASE_URL" -f catalogue_seed.sql
--
-- 30 approved, freely available resources, each tagged with the skills it
-- covers, its level and a duration. Every skill the seeded roles require
-- (Backend Developer, Data Analyst) has at least one resource at or above
-- the required level, so roadmaps for those roles are never empty.
-- Durations prefixed with ~ are curator estimates, not provider claims.
--
-- Safe to run again: learning_item has no natural key, so a resource's
-- source_url is treated as its identity and an existing one is left alone
-- (including any moderation change an administrator made since).
-- Unknown skill names fail the whole run instead of seeding untagged rows.
-- =====================================================================

BEGIN;

-- Serialise concurrent runs of this file (there is no unique key to lean on).
LOCK TABLE learning_item IN SHARE ROW EXCLUSIVE MODE;

CREATE TEMP TABLE ua8_resource (
  title text, description text, item_type text, level text, duration text,
  source_url text, source text
);

INSERT INTO ua8_resource VALUES
  ('The Python Tutorial',
   'The official tour of Python: data structures, control flow, functions, modules, errors and classes, with runnable examples.',
   'course', 'beginner', '~10 hours', 'https://docs.python.org/3/tutorial/', 'Python Software Foundation'),
  ('Python for Everybody',
   'A complete first course in programming with Python, from variables and loops to files, web data and databases. Free book, videos and exercises.',
   'course', 'beginner', '~40 hours', 'https://www.py4e.com/', 'py4e.com'),
  ('Composing Programs',
   'A free textbook from UC Berkeley''s CS 61A on abstraction, higher-order functions, recursion, object-oriented design and interpreters, all in Python.',
   'course', 'intermediate', '~60 hours', 'https://composingprograms.com/', 'composingprograms.com'),
  ('PCEP: Certified Entry-Level Python Programmer',
   'Entry-level certification from the Python Institute covering Python syntax, data types, control flow, functions and exceptions.',
   'certification', 'beginner', '~30 hours of preparation', 'https://pythoninstitute.org/pcep', 'Python Institute'),
  ('PostgreSQL Tutorial',
   'The official PostgreSQL introduction: creating tables, querying, joins, aggregates, updates, views, foreign keys and transactions.',
   'course', 'beginner', '~4 hours', 'https://www.postgresql.org/docs/current/tutorial.html', 'PostgreSQL Global Development Group'),
  ('SQLBolt',
   'Short interactive lessons and exercises that teach SQL in the browser, from SELECT and filtering to joins, aggregates and changing data.',
   'course', 'beginner', '~3 hours', 'https://sqlbolt.com/', 'SQLBolt'),
  ('Select Star SQL',
   'An interactive book that builds intermediate SQL on one real dataset: aggregations, joins, subqueries and multi-step queries.',
   'course', 'intermediate', '~5 hours', 'https://selectstarsql.com/', 'Select Star SQL'),
  ('PostgreSQL: Data Definition',
   'The PostgreSQL manual chapter on designing tables: data types, defaults, constraints, primary and foreign keys, schemas and privileges.',
   'course', 'intermediate', '~4 hours', 'https://www.postgresql.org/docs/current/ddl.html', 'PostgreSQL Global Development Group'),
  ('Use The Index, Luke',
   'SQL indexing for developers: how B-tree indexes work, how WHERE clauses, joins and sorting use them, and how to read execution plans.',
   'course', 'advanced', '~8 hours', 'https://use-the-index-luke.com/', 'use-the-index-luke.com'),
  ('Docker: Get started',
   'Docker''s official introduction: what containers are, building an image, running and sharing containers, volumes and multi-container apps.',
   'course', 'beginner', '~3 hours', 'https://docs.docker.com/get-started/', 'Docker Docs'),
  ('Project: run a web app and its database with Docker Compose',
   'Follow the Compose quickstart to run a small Python web app with a second service, then adapt it to your own app with a Postgres container.',
   'project_idea', 'intermediate', '~3 hours', 'https://docs.docker.com/compose/gettingstarted/', 'Docker Docs'),
  ('Web API design best practices',
   'Microsoft''s guide to designing RESTful web APIs: resources and URIs, HTTP methods and status codes, pagination, filtering and versioning.',
   'course', 'intermediate', '~2 hours', 'https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design', 'Microsoft Learn'),
  ('FastAPI Tutorial: User Guide',
   'Step-by-step guide to building APIs with FastAPI: path and query parameters, request bodies, validation, dependencies, security, errors and testing.',
   'course', 'intermediate', '~8 hours', 'https://fastapi.tiangolo.com/tutorial/', 'FastAPI'),
  ('Project: a REST API backed by a SQL database',
   'Build a CRUD API for one resource with FastAPI and a SQL database, following the official SQL databases tutorial, then add tests and a second resource.',
   'project_idea', 'intermediate', '~6 hours', 'https://fastapi.tiangolo.com/tutorial/sql-databases/', 'FastAPI'),
  ('Flask Tutorial',
   'Flask''s official tutorial: build a small blog with routing, templates, a SQLite database, user authentication and tests.',
   'course', 'beginner', '~5 hours', 'https://flask.palletsprojects.com/en/stable/tutorial/', 'Pallets Projects'),
  ('pytest: Get started',
   'Install pytest and write your first tests: plain assertions, grouping tests in classes, expected exceptions and temporary directories.',
   'course', 'beginner', '~1 hour', 'https://docs.pytest.org/en/stable/getting-started.html', 'pytest'),
  ('MIT 6.006 Introduction to Algorithms',
   'MIT OpenCourseWare lectures, notes and problem sets on algorithm design and analysis: sorting, hashing, trees, graphs, shortest paths and dynamic programming.',
   'course', 'intermediate', '~80 hours', 'https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/', 'MIT OpenCourseWare'),
  ('Problem Solving with Algorithms and Data Structures using Python',
   'An interactive textbook on stacks, queues, linked lists, recursion, sorting, searching, trees and graphs, with runnable Python.',
   'course', 'beginner', '~30 hours', 'https://runestone.academy/ns/books/published/pythonds3/index.html', 'Runestone Academy'),
  ('Machine Learning Crash Course',
   'Google''s fast-paced introduction to machine learning: linear and logistic regression, classification, working with data, overfitting and neural networks.',
   'course', 'beginner', '~15 hours', 'https://developers.google.com/machine-learning/crash-course', 'Google for Developers'),
  ('Machine learning in Python with scikit-learn',
   'A course by the scikit-learn developers: predictive modelling, pipelines, cross-validation, hyperparameter tuning, linear models, trees and ensembles.',
   'course', 'intermediate', '~35 hours', 'https://inria.github.io/scikit-learn-mooc/', 'Inria'),
  ('10 minutes to pandas',
   'pandas'' own short introduction to Series and DataFrames: selecting, filtering, missing data, grouping, merging and reshaping.',
   'course', 'beginner', '~1 hour', 'https://pandas.pydata.org/docs/user_guide/10min.html', 'pandas'),
  ('Matplotlib quick start guide',
   'Matplotlib''s introduction to plotting in Python: figures and axes, plotting styles, labels, legends, colour maps and several plots in one figure.',
   'course', 'beginner', '~2 hours', 'https://matplotlib.org/stable/users/explain/quick_start.html', 'Matplotlib'),
  ('Project: analyse a public dataset',
   'Pick a dataset on Kaggle, clean it with pandas, answer three questions with charts, and write up what you found in a notebook.',
   'project_idea', 'intermediate', '~10 hours', 'https://www.kaggle.com/datasets', 'Kaggle'),
  ('Statistics and probability',
   'Free lessons and practice on describing data, distributions, probability, sampling, confidence intervals and significance tests.',
   'course', 'beginner', '~40 hours', 'https://www.khanacademy.org/math/statistics-probability', 'Khan Academy'),
  ('Pro Git',
   'The complete Git book, free online: basics, branching, remotes, collaboration workflows on GitHub, and how Git works internally.',
   'course', 'beginner', '~10 hours', 'https://git-scm.com/book/en/v2', 'git-scm.com'),
  ('MDN JavaScript Guide',
   'MDN''s guide to the JavaScript language: grammar and types, control flow, functions, objects, classes, promises and modules.',
   'course', 'beginner', '~10 hours', 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', 'MDN Web Docs'),
  ('Learn React',
   'The official React course: describing UI with components and JSX, adding interactivity with state, managing state, and escape hatches.',
   'course', 'beginner', '~8 hours', 'https://react.dev/learn', 'React'),
  ('OWASP Top 10',
   'The OWASP list of the ten most critical web application security risks, each with examples, prevention advice and references.',
   'course', 'intermediate', '~4 hours', 'https://owasp.org/projects/top-ten', 'OWASP Foundation'),
  ('OWASP Authentication Cheat Sheet',
   'Concrete guidance on implementing authentication: password storage and rules, generic login errors, multi-factor authentication and account recovery.',
   'course', 'intermediate', '~1 hour', 'https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html', 'OWASP Foundation'),
  ('AWS Certified Cloud Practitioner',
   'Foundational AWS certification covering cloud concepts, core AWS services, security, pricing and support.',
   'certification', 'beginner', '~25 hours of preparation', 'https://aws.amazon.com/certification/certified-cloud-practitioner/', 'Amazon Web Services');

-- Which skills each resource covers, and to what level.
CREATE TEMP TABLE ua8_tag (source_url text, skill_name text, coverage text);

INSERT INTO ua8_tag VALUES
  ('https://docs.python.org/3/tutorial/', 'Python', 'beginner'),
  ('https://docs.python.org/3/tutorial/', 'Programming Fundamentals', 'beginner'),
  ('https://www.py4e.com/', 'Programming Fundamentals', 'beginner'),
  ('https://www.py4e.com/', 'Python', 'beginner'),
  ('https://composingprograms.com/', 'Python', 'intermediate'),
  ('https://composingprograms.com/', 'Programming Fundamentals', 'intermediate'),
  ('https://pythoninstitute.org/pcep', 'Python', 'beginner'),
  ('https://www.postgresql.org/docs/current/tutorial.html', 'SQL Basics', 'beginner'),
  ('https://www.postgresql.org/docs/current/tutorial.html', 'Relational Database Design', 'beginner'),
  ('https://sqlbolt.com/', 'SQL Basics', 'beginner'),
  ('https://selectstarsql.com/', 'SQL Basics', 'intermediate'),
  ('https://www.postgresql.org/docs/current/ddl.html', 'Relational Database Design', 'intermediate'),
  ('https://www.postgresql.org/docs/current/ddl.html', 'SQL Basics', 'intermediate'),
  ('https://use-the-index-luke.com/', 'Query Optimization & Indexing', 'advanced'),
  ('https://use-the-index-luke.com/', 'Relational Database Design', 'advanced'),
  ('https://docs.docker.com/get-started/', 'Docker & Containerization', 'beginner'),
  ('https://docs.docker.com/compose/gettingstarted/', 'Docker & Containerization', 'intermediate'),
  ('https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design', 'REST API Design', 'intermediate'),
  ('https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design', 'HTTP & Web Fundamentals', 'intermediate'),
  ('https://fastapi.tiangolo.com/tutorial/', 'Backend Framework (Flask/FastAPI)', 'intermediate'),
  ('https://fastapi.tiangolo.com/tutorial/', 'REST API Design', 'intermediate'),
  ('https://fastapi.tiangolo.com/tutorial/sql-databases/', 'Backend Framework (Flask/FastAPI)', 'intermediate'),
  ('https://fastapi.tiangolo.com/tutorial/sql-databases/', 'REST API Design', 'intermediate'),
  ('https://fastapi.tiangolo.com/tutorial/sql-databases/', 'SQL Basics', 'beginner'),
  ('https://flask.palletsprojects.com/en/stable/tutorial/', 'Backend Framework (Flask/FastAPI)', 'beginner'),
  ('https://docs.pytest.org/en/stable/getting-started.html', 'Unit Testing', 'beginner'),
  ('https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/', 'Algorithms', 'intermediate'),
  ('https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/', 'Data Structures', 'intermediate'),
  ('https://runestone.academy/ns/books/published/pythonds3/index.html', 'Data Structures', 'beginner'),
  ('https://runestone.academy/ns/books/published/pythonds3/index.html', 'Algorithms', 'beginner'),
  ('https://developers.google.com/machine-learning/crash-course', 'Machine Learning Fundamentals', 'beginner'),
  ('https://inria.github.io/scikit-learn-mooc/', 'Machine Learning Fundamentals', 'intermediate'),
  ('https://inria.github.io/scikit-learn-mooc/', 'Python', 'intermediate'),
  ('https://pandas.pydata.org/docs/user_guide/10min.html', 'Data Analysis with Pandas', 'beginner'),
  ('https://matplotlib.org/stable/users/explain/quick_start.html', 'Data Visualization', 'beginner'),
  ('https://www.kaggle.com/datasets', 'Data Analysis with Pandas', 'intermediate'),
  ('https://www.kaggle.com/datasets', 'Data Visualization', 'intermediate'),
  ('https://www.kaggle.com/datasets', 'Data Cleaning & Wrangling', 'intermediate'),
  ('https://www.khanacademy.org/math/statistics-probability', 'Statistics Fundamentals', 'beginner'),
  ('https://git-scm.com/book/en/v2', 'Git & Version Control', 'beginner'),
  ('https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', 'JavaScript', 'beginner'),
  ('https://react.dev/learn', 'React', 'beginner'),
  ('https://owasp.org/projects/top-ten', 'Web Security Basics', 'intermediate'),
  ('https://owasp.org/projects/top-ten', 'Secure Coding Practices', 'intermediate'),
  ('https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html', 'Authentication & Authorization', 'intermediate'),
  ('https://aws.amazon.com/certification/certified-cloud-practitioner/', 'Cloud Fundamentals', 'beginner');

DO $$
DECLARE missing text;
BEGIN
  SELECT string_agg(DISTINCT t.skill_name, ', ') INTO missing
  FROM ua8_tag t LEFT JOIN skill s ON s.skill_name = t.skill_name
  WHERE s.skill_id IS NULL;
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'Load the taxonomy seeds before catalogue_seed.sql; unknown skills: %', missing;
  END IF;
  IF EXISTS (SELECT 1 FROM ua8_resource r
             WHERE NOT EXISTS (SELECT 1 FROM ua8_tag t WHERE t.source_url = r.source_url)) THEN
    RAISE EXCEPTION 'Every resource in catalogue_seed.sql needs at least one skill tag';
  END IF;
END $$;

INSERT INTO learning_item
  (title, description, item_type, level, duration, source_url, source, moderation_state)
SELECT r.title, r.description, r.item_type::learning_item_type, r.level::skill_level,
       r.duration, r.source_url, r.source, 'approved'::moderation_state
FROM ua8_resource r
WHERE NOT EXISTS (SELECT 1 FROM learning_item li WHERE li.source_url = r.source_url);

INSERT INTO learning_item_skill (item_id, skill_id, coverage_level)
SELECT li.item_id, s.skill_id, t.coverage::skill_level
FROM ua8_tag t
JOIN learning_item li ON li.source_url = t.source_url
JOIN skill s ON s.skill_name = t.skill_name
ON CONFLICT (item_id, skill_id) DO NOTHING;

DROP TABLE ua8_tag;
DROP TABLE ua8_resource;

COMMIT;
