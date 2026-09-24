-- TEST: Multi-statement migration that fails partway through a transaction
-- EXPECTED: Full rollback — none of the statements should persist
-- BEHAVIOUR: Verifies that simply-migrate wraps migrations in a transaction
--            and that partial state is never committed on failure

BEGIN;

-- Step 1: succeeds
ALTER TABLE accounts ADD COLUMN tier TEXT NOT NULL DEFAULT 'standard';

-- Step 2: succeeds
UPDATE accounts SET tier = 'premium' WHERE balance > 750;

-- Step 3: intentional failure — column does not exist
UPDATE accounts SET nonexistent_column = 'oops' WHERE id = 1;

-- Step 4: should never execute
ALTER TABLE accounts ADD COLUMN should_not_exist BOOLEAN;

COMMIT;
