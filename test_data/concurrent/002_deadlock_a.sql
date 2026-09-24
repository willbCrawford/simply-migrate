-- TEST: Deadlock participant A
-- EXPECTED: One of A or B will be chosen as the deadlock victim by PG
--           and receive PG error 40P01 (deadlock_detected); the other commits
-- BEHAVIOUR: Run concurrent/003_deadlock_b.sql simultaneously in a second session
-- SETUP: Start both sessions within a few seconds of each other

BEGIN;

-- Lock row 1 first
UPDATE lock_test_table SET value = 'a_locked', updated_at = now() WHERE id = 1;

-- Simulate work before attempting the second lock
SELECT pg_sleep(2);

-- Now attempt to lock row 2 — B has already locked it, deadlock forms
UPDATE lock_test_table SET value = 'a_locked', updated_at = now() WHERE id = 2;

COMMIT;
