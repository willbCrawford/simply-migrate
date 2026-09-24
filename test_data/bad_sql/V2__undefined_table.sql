-- TEST: Reference to a table that does not exist
-- EXPECTED: PG error 42P01 (undefined_table)
-- BEHAVIOUR: Should fail immediately, no side effects

ALTER TABLE this_table_does_not_exist
    ADD COLUMN new_col TEXT;
