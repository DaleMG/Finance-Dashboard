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


def get_transactions(search_text=None, category_id=None):
    """Return transactions, optionally filtered by merchant text and category."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            transactions.id,
            transactions.date,
            transactions.merchant,
            transactions.amount,
            transactions.category_id,
            transactions.notes,
            categories.name
        FROM transactions
        LEFT JOIN categories ON transactions.category_id = categories.id
        WHERE 1 = 1
    """
    parameters = []

    if search_text:
        query += " AND LOWER(transactions.merchant) LIKE ?"
        parameters.append(f"%{search_text.strip().lower()}%")

    if category_id == "uncategorized":
        query += " AND transactions.category_id IS NULL"
    elif category_id is not None:
        query += " AND transactions.category_id = ?"
        parameters.append(category_id)

    query += " ORDER BY transactions.date DESC, transactions.id DESC"

    cursor.execute(query, parameters)

    transactions = cursor.fetchall()

    conn.close()

    return transactions


def update_transaction(transaction_id, date, merchant, amount, category_id=None, notes=None):
    """Update a transaction's editable fields."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE transactions
        SET date = ?, merchant = ?, amount = ?, category_id = ?, notes = ?
        WHERE id = ?
    """, (date, merchant, amount, category_id, notes, transaction_id))

    conn.commit()
    conn.close()


def update_transactions_category(transaction_ids, category_id):
    """Update the category for multiple transactions."""
    if not transaction_ids:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    cursor.executemany(
        """
        UPDATE transactions
        SET category_id = ?
        WHERE id = ?
        """,
        [(category_id, transaction_id) for transaction_id in transaction_ids],
    )

    updated_count = len(transaction_ids)

    conn.commit()
    conn.close()

    return updated_count


def delete_transaction(transaction_id):
    """Delete a transaction by id."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM transactions
        WHERE id = ?
    """, (transaction_id,))

    conn.commit()
    conn.close()


def add_budget(category_id, budget_amount):
    """Insert or replace a budget for a category."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO budgets (category_id, month, budget_amount)
        VALUES (?, ?, ?)
        ON CONFLICT(category_id, month)
        DO UPDATE SET budget_amount = excluded.budget_amount
    """, (category_id, "default", budget_amount))

    conn.commit()
    conn.close()


def get_budgets():
    """Return all saved category budgets."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT budgets.id, budgets.month, budgets.budget_amount, categories.id, categories.name
        FROM budgets
        INNER JOIN categories ON budgets.category_id = categories.id
        ORDER BY categories.name
    """)

    budgets = cursor.fetchall()

    conn.close()

    return budgets


def delete_budget(budget_id):
    """Delete a budget by id."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM budgets
        WHERE id = ?
    """, (budget_id,))

    conn.commit()
    conn.close()


def get_dashboard_summary():
    """Return high-level spending and budget totals for the dashboard."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS transaction_count,
            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) AS total_spending
        FROM transactions
    """)
    transaction_summary = cursor.fetchone()

    cursor.execute("""
        SELECT COALESCE(SUM(budget_amount), 0) AS total_budget
        FROM budgets
    """)
    budget_summary = cursor.fetchone()

    conn.close()

    transaction_count = transaction_summary[0]
    total_spending = float(transaction_summary[1])
    total_budget = float(budget_summary[0])

    return {
        "transaction_count": transaction_count,
        "total_spending": total_spending,
        "total_budget": total_budget,
        "remaining_budget": total_budget - total_spending,
    }


def get_category_spending():
    """Return total spending by category for the dashboard."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COALESCE(categories.name, 'Uncategorized') AS category_name,
            COALESCE(SUM(ABS(transactions.amount)), 0) AS total_spending
        FROM transactions
        LEFT JOIN categories ON transactions.category_id = categories.id
        WHERE transactions.amount < 0
        GROUP BY COALESCE(categories.name, 'Uncategorized')
        ORDER BY total_spending DESC, category_name
    """)

    category_spending = cursor.fetchall()

    conn.close()

    return category_spending
