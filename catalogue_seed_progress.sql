-- UA-8: Hemanth's five curated resources for progress/evidence testing.
-- Run after Alembic and taxonomy_seed_progress.sql; see docs/SPRINT2_SEEDS.md.
-- This shared seed-data contribution is not a new M4 runtime writer.
-- Durations prefixed with ~ are curator estimates, not provider claims.
BEGIN;

-- The schema has no resource natural-key constraint. Serialize this short
-- seed transaction so concurrent runs cannot create duplicate resources.
LOCK TABLE learning_item IN SHARE ROW EXCLUSIVE MODE;

DO $$
BEGIN
    IF (SELECT count(*) FROM skill WHERE skill_name IN (
        'Software Testing Fundamentals', 'Integration Testing', 'API Testing',
        'Test Automation', 'Code Coverage Analysis'
    )) <> 5 THEN
        RAISE EXCEPTION 'Run taxonomy_seed_progress.sql before catalogue_seed_progress.sql';
    END IF;
END $$;

WITH resources(title, description, level, duration, source_url, source, skill_names) AS (
    VALUES
    (
        'Testing From The Inside: Unit Testing Edition',
        'Learn unit-testing fundamentals and practise testing code from the inside.',
        'beginner', '~2 hours',
        'https://testautomationu.applitools.com/unit-testing/',
        'Test Automation University', ARRAY['Software Testing Fundamentals']
    ),
    (
        'Introduction to pytest',
        'Build a Python test project with assertions, fixtures, parametrization and plugins.',
        'beginner', '~3 hours',
        'https://testautomationu.applitools.com/pytest-tutorial/index.html',
        'Test Automation University', ARRAY['Test Automation']
    ),
    (
        'API Testing in Python',
        'Build an API automation framework with requests, response assertions and schema validation.',
        'intermediate', '~3 hours',
        'https://testautomationu.applitools.com/python-api-testing/',
        'Test Automation University', ARRAY['API Testing', 'Integration Testing']
    ),
    (
        'Setting a Foundation for Successful Test Automation',
        'Plan a test-automation initiative and consider appropriate tools and automation practices.',
        'beginner', '~1 hour',
        'https://testautomationu.applitools.com/setting-a-foundation-for-successful-test-automation/',
        'Test Automation University', ARRAY['Test Automation']
    ),
    (
        'Black-box and White-box Testing',
        'Study testing adequacy, test selection and structural testing to assess a test suite.',
        'intermediate', '26 hours',
        'https://www.coursera.org/learn/black-box-white-box-testing',
        'Coursera', ARRAY['Code Coverage Analysis']
    )
), inserted AS (
    INSERT INTO learning_item (
        title, description, item_type, level, duration, source_url, source, moderation_state
    )
    SELECT r.title, r.description, 'course'::learning_item_type, r.level::skill_level,
           r.duration, r.source_url, r.source, 'approved'::moderation_state
    FROM resources r
    WHERE NOT EXISTS (
        SELECT 1 FROM learning_item existing
        WHERE existing.title = r.title AND existing.source_url = r.source_url
    )
    RETURNING item_id, title, source_url
), matching_items AS (
    -- Data-modifying CTE inserts are not visible in the table snapshot below.
    SELECT item_id, title, source_url FROM inserted
    UNION ALL
    SELECT item_id, title, source_url FROM learning_item
)
INSERT INTO learning_item_skill (item_id, skill_id, coverage_level)
SELECT item.item_id, skill.skill_id, r.level::skill_level
FROM resources r
JOIN matching_items item ON item.title = r.title AND item.source_url = r.source_url
JOIN skill ON skill.skill_name = ANY(r.skill_names)
ON CONFLICT (item_id, skill_id) DO NOTHING;

-- Existing metadata and moderation decisions are never overwritten on reruns.
COMMIT;
