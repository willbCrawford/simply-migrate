-- TEST: Migration that exceeds statement timeout via pg_sleep
-- EXPECTED: PG error 57014 (query_canceled) if statement_timeout is set
-- BEHAVIOUR: Hangs indefinitely if no timeout is configured — use to verify
--            that simply-migrate enforces or respects statement_timeout
-- SETUP: Set a short timeout on the connection before running:

SET statement_timeout = '3s';

SELECT pg_sleep(30);
