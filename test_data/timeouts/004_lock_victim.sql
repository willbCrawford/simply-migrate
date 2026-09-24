-- TEST: Migration that attempts to alter a table held by 003_lock_holder.sql
-- EXPECTED: PG error 55P03 (lock_not_available) when lock_timeout fires
-- BEHAVIOUR: Run concurrently with 003_lock_holder.sql
-- SETUP: Set lock_timeout = '2s' on this connection before running

SET lock_timeout = '2s';

ALTER TABLE lock_test_table ADD COLUMN victim_col TEXT;
