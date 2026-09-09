-- Hardened / Secure E-Commerce Database Reference

-- 1. Table Schema with strict Primary Key and Constraints
CREATE TABLE secure_users (
    user_id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(60) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

-- 2. Data Rows with Salted Bcrypt Password Hashes and Tokenized Identifiers
INSERT INTO secure_users (user_id, username, password_hash, email, created_at) VALUES
('b3f1c840-7e12-4c22-b91e-8a21f7e91d01', 'sec_alice', '$2b$12$e8Y5M3o6wJ6n7GzDkH2P4eM0s3L1q8r7v9t2u4w6x8y0z1a2b3c4d', 'alice@securecorp.com', '2026-09-01 10:00:00'),
('c4a2d951-8f23-5d33-ca2f-9b32e8f02e02', 'sec_bob', '$2b$12$K1j2H3g4F5d6S7a8P9o0I1u2Y3t4R5e6W7q8E9r0T1y2U3i4O5p6A', 'bob@securecorp.com', '2026-09-01 11:30:00');

-- 3. Tokenized Payment Vault Table
CREATE TABLE secure_payments (
    payment_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    payment_token VARCHAR(64) NOT NULL,
    card_last4 CHAR(4) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL
);

INSERT INTO secure_payments (payment_id, user_id, payment_token, card_last4, amount) VALUES
('p_9901', 'b3f1c840-7e12-4c22-b91e-8a21f7e91d01', 'tok_visa_ch_3N8p2e2eZvKYlo2C01234567', '0366', 149.99);

-- 4. Parameterized Query (Safe from SQL Injection)
SELECT * FROM secure_users WHERE username = ? AND is_active = 1;

-- 5. Principle of Least Privilege Grant
GRANT SELECT, INSERT, UPDATE ON secure_store.secure_users TO 'app_service'@'10.0.0.%';
