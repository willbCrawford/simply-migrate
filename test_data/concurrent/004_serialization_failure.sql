-- TEST: Serialization failure under REPEATABLE READ isolation
-- EXPECTED: PG error 40001 (serialization_failure) on one concurrent session
-- BEHAVIOUR: Run two copies of this script simultaneously against the same DB.
--            The second committing session will fail with a serialization error.
-- PURPOSE: Verifies that simply-migrate surfaces serialization errors correctly
--          rather than silently committing stale data

BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- Read the current total balance (snapshot taken here)
SELECT sum(balance) AS total FROM accounts;

-- Simulate processing time — the other session modifies balances during this gap
SELECT pg_sleep(3);

-- Write based on what we read — if the snapshot is now stale, PG will abort
UPDATE accounts
SET balance = balance + 100
WHERE id = 1;

COMMIT;
