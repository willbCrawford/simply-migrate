-- TEST: Two sessions attempt to CREATE the same index simultaneously
-- EXPECTED: One session succeeds; the other receives PG error 42P07 (duplicate_table)
--           or blocks until the first completes (depending on PG version and timing)
-- BEHAVIOUR: Run two copies simultaneously to test how simply-migrate handles
--            duplicate object creation under concurrent tenant migrations
-- NOTE: CREATE INDEX CONCURRENTLY cannot run inside a transaction block

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lock_test_value
    ON lock_test_table (value);
