import sqlite3

DB_NAME = "database/budget.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER,
            notes TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            budget_amount REAL NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            UNIQUE(category_id, month)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchant_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant TEXT NOT NULL UNIQUE,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    conn.commit()
    conn.close()


def add_category(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM categories
        WHERE LOWER(name) = LOWER(?)
    """, (name,))

    existing_category = cursor.fetchone()

    if existing_category is not None:
        conn.close()
        raise sqlite3.IntegrityError("Category already exists")

    cursor.execute("""
        INSERT INTO categories (name)
        VALUES (?)
    """, (name,))

    conn.commit()
    conn.close()


def get_categories():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM categories
        ORDER BY name
    """)

    categories = cursor.fetchall()

    conn.close()

    return categories


def delete_category(category_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM categories
        WHERE id = ?
    """, (category_id,))

    conn.commit()
    conn.close()


def add_transaction(date, merchant, amount, category_id=None, notes=None):
    """Insert a single transaction and return the new row id."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO transactions (date, merchant, amount, category_id, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (date, merchant, amount, category_id, notes))

    transaction_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return transaction_id


def add_transactions(transactions):
    """Insert multiple transactions and return the number of rows added."""
    conn = get_connection()
    cursor = conn.cursor()

    rows_to_insert = []

    for transaction in transactions:
        rows_to_insert.append(
            (
                transaction["date"],
                transaction["merchant"],
                transaction["amount"],
                transaction.get("category_id"),
                transaction.get("notes"),
            )
        )

    cursor.executemany("""
        INSERT INTO transactions (date, merchant, amount, category_id, notes)
        VALUES (?, ?, ?, ?, ?)
    """, rows_to_insert)

    inserted_count = len(rows_to_insert)

    conn.commit()
    conn.close()

    return inserted_count


def get_transactions():
    """Return all transactions ordered by newest date first."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, date, merchant, amount, category_id, notes
        FROM transactions
        ORDER BY date DESC, id DESC
    """)

    transactions = cursor.fetchall()

    conn.close()

    return transactions
