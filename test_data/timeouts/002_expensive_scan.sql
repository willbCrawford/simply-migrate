-- TEST: Heavy sequential scan on a large generated dataset
-- EXPECTED: Slow query; triggers statement_timeout if configured tightly
-- BEHAVIOUR: Use to verify timeout handling on real query load (not just sleep)
-- SETUP: statement_timeout = '5s' will reliably cancel this

-- Generate ~5M rows in a CTE and scan them all
WITH big AS (
    SELECT generate_series(1, 5000000) AS n
)
SELECT count(*)
FROM big
WHERE mod(n, 3) = 0;
