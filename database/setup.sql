
-- =========================================
-- DATABASE QUERY OPTIMIZER
-- Sample Database Setup
-- =========================================

CREATE DATABASE IF NOT EXISTS query_optimizer_db;

USE query_optimizer_db;

-- Reset existing tables
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

-- =========================================
-- 1. CUSTOMERS TABLE
-- =========================================

CREATE TABLE customers (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- =========================================
-- 2. ORDERS TABLE
-- =========================================

CREATE TABLE orders (
    id BIGINT PRIMARY KEY,
    customer_id INT NOT NULL,
    created_at DATETIME NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL
) ENGINE=InnoDB;

-- Note:
-- We intentionally do not create an index on
-- customer_id or created_at.
-- This is necessary for our slow query demo.

-- =========================================
-- 3. GENERATE SAMPLE DATA
-- =========================================

CREATE TEMPORARY TABLE digits (
    n TINYINT NOT NULL PRIMARY KEY
);

INSERT INTO digits (n)
VALUES (0), (1), (2), (3), (4),
       (5), (6), (7), (8), (9);

-- Generate 1,000 customers

INSERT INTO customers (id, name, email)
SELECT
    n,
    CONCAT('Customer ', n),
    CONCAT('customer', n, '@example.com')
FROM (
    SELECT
        a.n + (10 * b.n) + (100 * c.n) + 1 AS n
    FROM digits a
    CROSS JOIN digits b
    CROSS JOIN digits c
) AS numbers;

-- Generate 100,000 orders

INSERT INTO orders (
    id,
    customer_id,
    created_at,
    total_amount
)
SELECT
    n + 1,
    MOD(n, 1000) + 1,
    DATE_ADD(
        '2023-01-01 00:00:00',
        INTERVAL n MINUTE
    ),
    ROUND(100 + MOD(n * 37, 90000) / 100, 2)
FROM (
    SELECT
        a.n
        + (10 * b.n)
        + (100 * c.n)
        + (1000 * d.n)
        + (10000 * e.n) AS n
    FROM digits a
    CROSS JOIN digits b
    CROSS JOIN digits c
    CROSS JOIN digits d
    CROSS JOIN digits e
) AS numbers;

DROP TEMPORARY TABLE digits;

-- Update database statistics
ANALYZE TABLE orders;
ANALYZE TABLE customers;

-- =========================================
-- 4. CHECK SAMPLE DATA
-- =========================================

SELECT COUNT(*) AS total_customers
FROM customers;

SELECT COUNT(*) AS total_orders
FROM orders;

-- Check existing indexes
SHOW INDEX FROM orders;

-- Test slow query
EXPLAIN
SELECT *
FROM orders
WHERE customer_id = 105
ORDER BY created_at DESC
LIMIT 10;
