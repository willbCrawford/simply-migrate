-- TEST: Syntax error — missing closing parenthesis
-- EXPECTED: PG error 42601 (syntax_error)
-- BEHAVIOUR: Should fail immediately, no table created

CREATE TABLE bad_syntax (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
-- intentionally missing closing paren and semicolon
