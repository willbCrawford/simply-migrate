-- TEST: Drop an index that does not exist (without IF EXISTS guard)
-- EXPECTED: PG error 42704 (undefined_object)
-- BEHAVIOUR: Should fail immediately
-- NOTE: Tests that the runner does not swallow index errors silently

DROP INDEX idx_does_not_exist;
