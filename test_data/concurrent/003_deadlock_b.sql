-- TEST: Deadlock participant B
-- EXPECTED: One of A or B will be chosen as the deadlock victim by PG
--           and receive PG error 40P01 (deadlock_detected); the other commits
-- BEHAVIOUR: Run concurrently with concurrent/002_deadlock_a.sql
-- SETUP: Start both sessions within a few seconds of each other

BEGIN;

-- Lock row 2 first (opposite order to A — this creates the cycle)
UPDATE lock_test_table SET value = 'b_locked', updated_at = now() WHERE id = 2;

-- Simulate work before attempting the second lock
SELECT pg_sleep(2);

-- Now attempt to lock row 1 — A has already locked it, deadlock forms
UPDATE lock_test_table SET value = 'b_locked', updated_at = now() WHERE id = 1;

COMMIT;
