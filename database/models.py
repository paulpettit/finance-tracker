"""
Database setup and helper functions for the finance tracker.

WHAT YOU'LL LEARN HERE:
- How to create and connect to a SQLite database
- How to define tables using SQL
- How to insert and query data

SQLite stores everything in a single file (finance.db). No server needed.
"""

import sqlite3
import os

# Path to the database file — it lives in the project root
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'finance.db')


def get_connection():
    """
    Opens a connection to the SQLite database.
    Think of this like opening a file — you need to open it before reading/writing.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    # This makes query results act like dictionaries (row['column_name'])
    # instead of plain tuples (row[0], row[1], ...) — much easier to work with
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """
    Creates the database tables if they don't exist yet.
    This runs once when you first start the app.

    We have 2 tables:
    - accounts: Your bank/investment accounts (Chase, Fidelity, etc.)
    - transactions: Individual transactions from CSV imports

    TODO (Phase 3+): Add a 'balances' table for tracking account balances
    over time, which you'll need for the net worth chart.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ---- ACCOUNTS TABLE ----
    # Stores info about each of your financial accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            institution TEXT NOT NULL,
            account_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # account_type examples: "checking", "credit_card", "brokerage", "crypto", "savings"

    # ---- TRANSACTIONS TABLE ----
    # Stores every transaction imported from CSVs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'Uncategorized',
            source_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    ''')
    # source_file tracks which CSV this came from (helps with duplicate detection)

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


def add_account(name, institution, account_type):
    """
    Add a new account to the database.

    Example usage:
        add_account("Chase Checking", "chase", "checking")
        add_account("Amex Gold", "amex", "credit_card")
        add_account("Fidelity 401k", "fidelity", "brokerage")
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO accounts (name, institution, account_type) VALUES (?, ?, ?)',
        (name, institution, account_type)
    )
    conn.commit()
    account_id = cursor.lastrowid
    conn.close()
    return account_id


def add_transactions(transactions, account_id, source_file):
    """
    Insert a list of parsed transactions into the database.

    Each transaction should be a dictionary with:
        - date: string like "2024-01-15"
        - description: string like "AMAZON.COM"
        - amount: float like -52.99 (negative = money spent)
        - category: string like "Shopping" (optional)

    YOUR TASK: Later, add duplicate detection here!
    Hint: Check if a transaction with the same date, amount, and description
    already exists for this account before inserting.
    """
    conn = get_connection()
    cursor = conn.cursor()

    count = 0
    for t in transactions:
        cursor.execute(
            '''INSERT INTO transactions (account_id, date, description, amount, category, source_file)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (account_id, t['date'], t['description'], t['amount'],
             t.get('category', 'Uncategorized'), source_file)
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def get_all_transactions(account_id=None):
    """
    Retrieve transactions from the database.
    If account_id is provided, only get transactions for that account.
    Otherwise, get all transactions.

    Returns a list of Row objects (behave like dictionaries).
    """
    conn = get_connection()
    cursor = conn.cursor()

    if account_id:
        cursor.execute(
            'SELECT * FROM transactions WHERE account_id = ? ORDER BY date DESC',
            (account_id,)
        )
    else:
        cursor.execute('SELECT * FROM transactions ORDER BY date DESC')

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_accounts():
    """Retrieve all accounts from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM accounts ORDER BY institution')
    rows = cursor.fetchall()
    conn.close()
    return rows


# ---- Run this file directly to initialize the database ----
# In your terminal: python database/models.py
if __name__ == '__main__':
    initialize_database()
    print(f"Database created at: {DATABASE_PATH}")
