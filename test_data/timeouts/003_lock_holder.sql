-- TEST: Migration that immediately acquires an ACCESS EXCLUSIVE lock and holds it
-- EXPECTED: Any concurrent migration touching the same table will block until
--           lock_timeout fires (PG error 55P03)
-- BEHAVIOUR: Run this alongside 002_lock_victim.sql to exercise lock_timeout
-- SETUP: In a second session, set lock_timeout = '2s' before running the victim

BEGIN;

-- Grab an exclusive lock on the table
LOCK TABLE lock_test_table IN ACCESS EXCLUSIVE MODE;

-- Hold the lock long enough for a concurrent session to time out
SELECT pg_sleep(15);

COMMIT;
