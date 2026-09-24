-- TEST SETUP: Creates baseline tables used by the partial failure suite
-- Run this first to establish a clean state
-- EXPECTED: Succeeds cleanly

CREATE TABLE IF NOT EXISTS accounts (
    id         SERIAL PRIMARY KEY,
    name       TEXT    NOT NULL,
    balance    NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         SERIAL PRIMARY KEY,
    account_id INT  NOT NULL REFERENCES accounts(id),
    action     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO accounts (name, balance) VALUES
    ('alice', 1000),
    ('bob',   500);
