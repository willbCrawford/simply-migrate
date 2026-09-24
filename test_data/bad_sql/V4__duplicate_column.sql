-- TEST: Duplicate column name in CREATE TABLE
-- EXPECTED: PG error 42701 (duplicate_column)
-- BEHAVIOUR: Should fail immediately, no table created

CREATE TABLE duplicate_col (
    id   SERIAL PRIMARY KEY,
    name TEXT,
    name TEXT
);
