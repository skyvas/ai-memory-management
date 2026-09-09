-- Vulnerable E-Commerce Database Dump

-- 1. Table Schema missing primary key on sensitive table
CREATE TABLE users (
    username VARCHAR(50),
    password VARCHAR(100),
    email VARCHAR(100),
    ssn VARCHAR(11)
);

-- 2. Data Rows with Plaintext Passwords and SSNs
INSERT INTO users (username, password, email, ssn) VALUES
('alice_admin', 'SuperAdmin2026!', 'alice@store.com', '458-21-9982'),
('bob_developer', 'P@ssword123', 'bob@store.com', '987-65-4321'),
('charlie_customer', 'qwerty12345', 'charlie@gmail.com', '123-45-6789');

-- 3. Table Schema with orders
CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_name VARCHAR(100),
    credit_card VARCHAR(20),
    amount DECIMAL(10, 2)
);

-- 4. Data Rows with Plaintext Credit Card Numbers (Luhn-Valid)
INSERT INTO orders (order_id, customer_name, credit_card, amount) VALUES
(101, 'Alice Smith', '4532015112830366', 149.99),
(102, 'Bob Jones', '5424180123456789', 89.50),
(103, 'Charlie Brown', '378282246310005', 420.00);

-- 5. Insecure Dynamic Query Concatenation (SQL Injection)
SELECT * FROM users WHERE username = ' + user_input + ' AND password = ' + pass_input + ';

-- 6. Overly Permissive Privilege Grant
GRANT ALL PRIVILEGES ON *.* TO 'app_user'@'%';
