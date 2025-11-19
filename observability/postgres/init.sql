-- PostgreSQL initialization script for COMPASS demo
-- Creates payments table for sample application

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add some initial test data
INSERT INTO payments (id, amount, status) VALUES
    (1, 100.00, 'completed'),
    (2, 250.50, 'completed'),
    (3, 75.25, 'pending'),
    (4, 500.00, 'completed'),
    (5, 125.75, 'failed');

-- Reset sequence to continue from ID 6
-- This prevents auto-increment collisions with manual inserts above
SELECT setval('payments_id_seq', 5);

-- NOTE: Intentionally NO index on amount column
-- This allows the "missing_index" incident to demonstrate full table scans
-- To fix: CREATE INDEX idx_payments_amount ON payments(amount);
