-- TEST: DDL (CREATE TABLE) followed by failing DML within the same transaction
-- EXPECTED: Full rollback — the new table should NOT exist after failure
-- BEHAVIOUR: Verifies that DDL inside a transaction is rolled back correctly
--            in PostgreSQL (unlike MySQL, PG supports transactional DDL)

BEGIN;

CREATE TABLE transactional_ddl_test (
    id   SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL
);

INSERT INTO transactional_ddl_test (code) VALUES ('alpha');
INSERT INTO transactional_ddl_test (code) VALUES ('beta');

-- Intentional failure: violates the UNIQUE constraint
INSERT INTO transactional_ddl_test (code) VALUES ('alpha');

COMMIT;

-- Verify: this table should not exist if rollback worked correctly
-- SELECT * FROM transactional_ddl_test;
