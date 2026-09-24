-- TEST: Column with an invalid / nonexistent type
-- EXPECTED: PG error 42704 (undefined_object)
-- BEHAVIOUR: Should fail immediately, no table created

CREATE TABLE bad_type (
    id   SERIAL PRIMARY KEY,
    data NOTATYPE NOT NULL
);
