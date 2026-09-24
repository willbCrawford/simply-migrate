-- TEST: Uses SAVEPOINTs to recover from a known bad statement and continue
-- EXPECTED: Partial success — work before/after the savepoint persists,
--           only the bad statement between SAVEPOINT and ROLLBACK TO is lost
-- BEHAVIOUR: Tests whether simply-migrate handles or exposes savepoint semantics
--            This is an intentionally advanced/edge-case script

BEGIN;

ALTER TABLE accounts ADD COLUMN notes TEXT;

SAVEPOINT before_bad_update;

-- This will fail: referencing a column that does not exist
UPDATE accounts SET nonexistent = 'bad' WHERE id = 1;

-- Roll back only to the savepoint, not the whole transaction
ROLLBACK TO SAVEPOINT before_bad_update;

-- This should still succeed and commit
UPDATE accounts SET notes = 'recovered' WHERE id = 1;

COMMIT;
