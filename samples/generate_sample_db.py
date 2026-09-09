"""Generates realistic enterprise-scale benchmark databases for dbsec testing.

Produces:
- samples/vulnerable_enterprise.db: 10,500+ records with rich variety of vulnerabilities
  (unhashed passwords, MD5/SHA-1 hashes, Luhn credit cards, SSNs, AWS/GitHub/Stripe keys,
  private RSA keys, missing primary keys, insecure PRAGMAs).
- samples/secure_store.db: Hardened benchmark conforming to PCI-DSS and GDPR.
"""
import sqlite3
import hashlib
import random
from pathlib import Path

SAMPLE_DIR = Path("samples")
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def generate_luhn_card(prefix: str, length: int) -> str:
    """Generates a mathematically valid Luhn credit card number."""
    digits = [int(ch) for ch in prefix]
    while len(digits) < length - 1:
        digits.append(random.randint(0, 9))
    
    # Calculate Luhn checksum digit
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 0:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    
    check_digit = (10 - (checksum % 10)) % 10
    digits.append(check_digit)
    return "".join(str(d) for d in digits)


def generate_vulnerable_enterprise_db(file_path: Path):
    if file_path.exists():
        file_path.unlink()

    conn = sqlite3.connect(str(file_path))
    cursor = conn.cursor()

    # Configure Insecure PRAGMAs
    cursor.execute("PRAGMA secure_delete = 0")  # OFF
    cursor.execute("PRAGMA foreign_keys = 0")   # OFF
    cursor.execute("PRAGMA journal_mode = DELETE")

    # 1. Customers Table (3,000 rows) - PII Leaks (SSNs, Phones, Emails)
    cursor.execute("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        ssn TEXT,
        street_address TEXT,
        created_at TEXT
    )
    """)

    customers_data = []
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]

    for i in range(1, 3001):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        phone = f"{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        ssn = f"{random.randint(100, 999):03d}-{random.randint(10, 99):02d}-{random.randint(1000, 9999):04d}"
        addr = f"{random.randint(100, 9999)} Market St, Suite {i}, San Francisco, CA"
        customers_data.append((name, email, phone, ssn, addr, "2026-01-15 10:00:00"))

    cursor.executemany(
        "INSERT INTO customers (full_name, email, phone, ssn, street_address, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        customers_data,
    )

    # 2. User Credentials Table (2,500 rows) - Passwords, MD5, SHA-1, Trivial Passwords
    cursor.execute("""
    CREATE TABLE user_credentials (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'standard',
        last_login TEXT
    )
    """)

    creds_data = []
    default_passwords = ["admin", "password", "123456", "root", "qwerty"]
    plaintext_passwords = ["P@ssword2026!", "SecretSummer!", "Welcome123", "CompanyAdmin99!", "Tiger2026"]
    
    for i in range(1, 2501):
        u_name = f"user_{i:04d}"
        mod = i % 5
        if mod == 0:
            # Trivial default password
            pw = random.choice(default_passwords)
        elif mod == 1:
            # Plaintext password
            pw = random.choice(plaintext_passwords)
        elif mod == 2:
            # Cryptographically broken MD5
            pw = hashlib.md5(f"pass_{i}".encode()).hexdigest()
        elif mod == 3:
            # Deprecated SHA-1
            pw = hashlib.sha1(f"pass_{i}".encode()).hexdigest()
        else:
            # Secure bcrypt format
            pw = "$2b$12$K8y0WqD9pQz5M1V4hN7jLu8v7p9m1n3b5v7x9z1a3c5e7g9i1k3m5"
        
        creds_data.append((u_name, pw, "user" if i > 10 else "admin", "2026-03-01 08:30:00"))

    cursor.executemany(
        "INSERT INTO user_credentials (username, password, role, last_login) VALUES (?, ?, ?, ?)",
        creds_data,
    )

    # 3. Payment Cards Table (2,000 rows) - Luhn-valid Credit Cards
    cursor.execute("""
    CREATE TABLE payment_cards (
        card_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        cardholder_name TEXT,
        card_number TEXT NOT NULL,
        exp_date TEXT,
        cvv TEXT
    )
    """)

    cards_data = []
    # Visa (4), Mastercard (51), Amex (37), Discover (6011)
    card_prefixes = [("4", 16), ("51", 16), ("37", 15), ("6011", 16)]

    for i in range(1, 2001):
        pfx, length = random.choice(card_prefixes)
        card_num = generate_luhn_card(pfx, length)
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        exp = f"{random.randint(1, 12):02d}/2{random.randint(7, 9)}"
        cvv = f"{random.randint(100, 999)}"
        cards_data.append((i, f"{fn} {ln}", card_num, exp, cvv))

    cursor.executemany(
        "INSERT INTO payment_cards (customer_id, cardholder_name, card_number, exp_date, cvv) VALUES (?, ?, ?, ?, ?)",
        cards_data,
    )

    # 4. API Keys & Cloud Secrets Table (1,000 rows) - AWS, GitHub, Stripe, Private Keys
    cursor.execute("""
    CREATE TABLE api_keys_and_tokens (
        key_id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT,
        access_token TEXT,
        private_key TEXT,
        created_at TEXT
    )
    """)

    keys_data = []
    rsa_dummy_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y3e...TRUNCATED_KEY...IDAQAB\n-----END RSA PRIVATE KEY-----"

    for i in range(1, 1001):
        mod = i % 4
        if mod == 0:
            svc = "AWS_S3"
            token = f"AKIA{i:04d}IOSFODNN7EXA"
            pkey = None
        elif mod == 1:
            svc = "GitHub_CI"
            token = f"ghp_{hashlib.sha1(str(i).encode()).hexdigest()}"
            pkey = None
        elif mod == 2:
            svc = "Stripe_Payments"
            token = f"sk_test_51A2B3C4D5E6F7G8H9I0J1K2L{i:03d}"
            pkey = None
        else:
            svc = "Internal_SSH"
            token = None
            pkey = rsa_dummy_key
        
        keys_data.append((svc, token, pkey, "2026-02-10 14:00:00"))

    cursor.executemany(
        "INSERT INTO api_keys_and_tokens (service_name, access_token, private_key, created_at) VALUES (?, ?, ?, ?)",
        keys_data,
    )

    # 5. Audit Logs Table (1,500 rows) - SQL Injection traces & Stored Procs
    cursor.execute("""
    CREATE TABLE audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        query_text TEXT,
        ip_address TEXT,
        timestamp TEXT
    )
    """)

    logs_data = []
    injections = [
        "SELECT * FROM users WHERE username = 'admin' + var_input",
        "SELECT * FROM accounts WHERE id = 101 OR '1'='1'",
        "EXEC master..xp_cmdshell 'powershell.exe -c Get-Process'",
        "SELECT * FROM products WHERE id = 1 AND SLEEP(5)",
        "GRANT ALL PRIVILEGES ON *.* TO 'remote_app'@'%'",
    ]

    for i in range(1, 1501):
        if i % 10 == 0:
            q = random.choice(injections)
            ev = "QUERY_EXECUTION_SUSPICIOUS"
        else:
            q = f"SELECT user_id, username FROM user_credentials WHERE user_id = {i}"
            ev = "QUERY_EXECUTION_NORMAL"
        ip = f"192.168.1.{random.randint(2, 254)}"
        logs_data.append((ev, q, ip, "2026-03-05 12:00:00"))

    cursor.executemany(
        "INSERT INTO audit_logs (event_type, query_text, ip_address, timestamp) VALUES (?, ?, ?, ?)",
        logs_data,
    )

    # 6. Unconstrained Profiles (500 rows) - Missing Primary Key & Insecure Default Role
    cursor.execute("""
    CREATE TABLE unconstrained_profiles (
        profile_id INTEGER,
        username TEXT,
        is_admin INTEGER DEFAULT 1,
        bio TEXT
    )
    """)

    profiles_data = []
    for i in range(1, 501):
        profiles_data.append((i, f"user_{i}", 1, f"Security test bio for profile {i}"))

    cursor.executemany(
        "INSERT INTO unconstrained_profiles (profile_id, username, is_admin, bio) VALUES (?, ?, ?, ?)",
        profiles_data,
    )

    # Create a trigger with dynamic SQL
    cursor.execute("""
    CREATE TRIGGER trg_audit_users AFTER INSERT ON customers
    BEGIN
        INSERT INTO audit_logs (event_type, query_text, ip_address, timestamp)
        VALUES ('CUSTOMER_ADDED', 'INSERT INTO customers ... ' || new.full_name, '127.0.0.1', datetime('now'));
    END;
    """)

    conn.commit()
    conn.close()
    print(f"Generated {file_path} with 10,500 records.")


def generate_secure_store_db(file_path: Path):
    if file_path.exists():
        file_path.unlink()

    conn = sqlite3.connect(str(file_path))
    cursor = conn.cursor()

    cursor.execute("PRAGMA auto_vacuum = 1")    # FULL (persists in header)
    cursor.execute("PRAGMA journal_mode = WAL")  # WAL (persists in header)
    cursor.execute("PRAGMA secure_delete = 1")  # ON
    cursor.execute("PRAGMA foreign_keys = 1")   # ON

    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at TEXT
    )
    """)

    users_data = []
    for i in range(1, 501):
        users_data.append((
            f"secure_user_{i}",
            "$2b$12$e8Y7z6X5w4V3u2T1s0R.OuK8y0WqD9pQz5M1V4hN7jLu8v7p9m1n3",
            "user",
            "2026-01-01 00:00:00"
        ))

    cursor.executemany(
        "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
        users_data,
    )

    cursor.execute("""
    CREATE TABLE tokenized_payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        payment_token TEXT NOT NULL,
        card_brand TEXT NOT NULL,
        last_four TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    payments_data = []
    for i in range(1, 501):
        payments_data.append((
            i,
            f"tok_visa_{hashlib.sha256(str(i).encode()).hexdigest()[:24]}",
            "Visa",
            f"{i % 10000:04d}"
        ))

    cursor.executemany(
        "INSERT INTO tokenized_payments (user_id, payment_token, card_brand, last_four) VALUES (?, ?, ?, ?)",
        payments_data,
    )

    conn.commit()
    conn.close()
    print(f"Generated {file_path} with 1,000 secure records.")


if __name__ == "__main__":
    generate_vulnerable_enterprise_db(SAMPLE_DIR / "vulnerable_enterprise.db")
    generate_secure_store_db(SAMPLE_DIR / "secure_store.db")
