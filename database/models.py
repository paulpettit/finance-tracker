"""
Database setup and helper functions for the finance tracker.

WHAT YOU'LL LEARN HERE:
- How to create and connect to a SQLite database
- How to define tables using SQL
- How to insert and query data
- How database migrations work (adding columns to existing tables)
- How a rules engine stores and applies categorization logic

SQLite stores everything in a single file (finance.db). No server needed.
"""

import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'finance.db')


def get_connection():
    """Opens a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """
    Creates all database tables if they don't exist.

    TABLES:
    - accounts: Your bank/investment accounts
    - transactions: Individual transactions (now with review status)
    - rules: Auto-categorization rules (Lunch Money-inspired)
    - budgets: Monthly spending limits per category
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            institution TEXT NOT NULL,
            account_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'Uncategorized',
            reviewed INTEGER DEFAULT 0,
            source_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            condition_field TEXT NOT NULL DEFAULT 'description',
            condition_op TEXT NOT NULL DEFAULT 'contains',
            condition_value TEXT NOT NULL,
            action_category TEXT,
            action_rename TEXT,
            enabled INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            month TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, month)
        )
    ''')

    # Migration: add 'reviewed' column to existing databases
    try:
        cursor.execute('SELECT reviewed FROM transactions LIMIT 1')
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE transactions ADD COLUMN reviewed INTEGER DEFAULT 0')
        print("Migration: Added 'reviewed' column to transactions")

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


# ==============================================================
# ACCOUNT FUNCTIONS
# ==============================================================

def add_account(name, institution, account_type):
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


def get_all_accounts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM accounts ORDER BY institution')
    rows = cursor.fetchall()
    conn.close()
    return rows


# ==============================================================
# TRANSACTION FUNCTIONS
# ==============================================================

def add_transactions(transactions, account_id, source_file):
    """
    Insert parsed transactions into the database.
    Applies rules to auto-categorize before inserting.
    Includes duplicate detection.
    Returns (count_inserted, count_skipped).
    """
    conn = get_connection()
    cursor = conn.cursor()
    rules = get_all_rules(enabled_only=True)

    count = 0
    skipped = 0
    for t in transactions:
        # Duplicate detection
        cursor.execute(
            '''SELECT id FROM transactions
               WHERE account_id = ? AND date = ? AND amount = ? AND description = ?''',
            (account_id, t['date'], t['amount'], t['description'])
        )
        if cursor.fetchone():
            skipped += 1
            continue

        # Apply rules
        category = t.get('category', 'Uncategorized')
        description = t['description']
        for rule in rules:
            if match_rule(rule, t):
                if rule['action_category']:
                    category = rule['action_category']
                if rule['action_rename']:
                    description = rule['action_rename']
                break

        cursor.execute(
            '''INSERT INTO transactions
               (account_id, date, description, amount, category, reviewed, source_file)
               VALUES (?, ?, ?, ?, ?, 0, ?)''',
            (account_id, t['date'], description, t['amount'], category, source_file)
        )
        count += 1

    conn.commit()
    conn.close()
    return count, skipped


def get_all_transactions(account_id=None):
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


def update_transaction_review(transaction_id, reviewed):
    """Mark a transaction as reviewed (1) or unreviewed (0)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE transactions SET reviewed = ? WHERE id = ?',
        (1 if reviewed else 0, transaction_id)
    )
    conn.commit()
    conn.close()


def update_transaction_category(transaction_id, category):
    """Update a transaction's category."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE transactions SET category = ? WHERE id = ?',
        (category, transaction_id)
    )
    conn.commit()
    conn.close()


def get_review_stats():
    """Get counts of reviewed vs unreviewed transactions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM transactions')
    total = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(*) as reviewed FROM transactions WHERE reviewed = 1')
    reviewed = cursor.fetchone()['reviewed']
    conn.close()
    return {'total': total, 'reviewed': reviewed, 'unreviewed': total - reviewed}


def get_all_categories():
    """Get a sorted list of all unique categories in use."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM transactions ORDER BY category')
    rows = cursor.fetchall()
    conn.close()
    return [r['category'] for r in rows]


# ==============================================================
# RULES ENGINE
# ==============================================================

def match_rule(rule, transaction):
    """
    Check if a transaction matches a rule's conditions.
    Supports: contains, equals (for descriptions), greater_than, less_than (for amounts).
    """
    field = rule['condition_field']
    op = rule['condition_op']
    value = rule['condition_value']

    if field == 'description':
        desc = transaction.get('description', '').upper()
        if op == 'contains':
            return value.upper() in desc
        elif op == 'equals':
            return value.upper() == desc
    elif field == 'amount':
        try:
            amount = float(transaction.get('amount', 0))
            threshold = float(value)
            if op == 'greater_than':
                return amount > threshold
            elif op == 'less_than':
                return amount < threshold
            elif op == 'equals':
                return abs(amount - threshold) < 0.01
        except (ValueError, TypeError):
            return False
    return False


def add_rule(name, condition_field, condition_op, condition_value,
             action_category=None, action_rename=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO rules (name, condition_field, condition_op, condition_value,
           action_category, action_rename) VALUES (?, ?, ?, ?, ?, ?)''',
        (name, condition_field, condition_op, condition_value,
         action_category, action_rename)
    )
    conn.commit()
    rule_id = cursor.lastrowid
    conn.close()
    return rule_id


def get_all_rules(enabled_only=False):
    conn = get_connection()
    cursor = conn.cursor()
    if enabled_only:
        cursor.execute('SELECT * FROM rules WHERE enabled = 1 ORDER BY priority DESC, id')
    else:
        cursor.execute('SELECT * FROM rules ORDER BY priority DESC, id')
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_rule(rule_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM rules WHERE id = ?', (rule_id,))
    conn.commit()
    conn.close()


def toggle_rule(rule_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE rules SET enabled = 1 - enabled WHERE id = ?', (rule_id,))
    conn.commit()
    conn.close()


def apply_rules_retroactively():
    """Re-apply all active rules to existing transactions. Returns update count."""
    conn = get_connection()
    cursor = conn.cursor()
    rules = get_all_rules(enabled_only=True)
    cursor.execute('SELECT * FROM transactions')
    all_txns = cursor.fetchall()

    updated = 0
    for txn in all_txns:
        txn_dict = dict(txn)
        for rule in rules:
            if match_rule(rule, txn_dict):
                new_cat = rule['action_category'] or txn_dict['category']
                new_desc = rule['action_rename'] or txn_dict['description']
                if new_cat != txn_dict['category'] or new_desc != txn_dict['description']:
                    cursor.execute(
                        'UPDATE transactions SET category = ?, description = ? WHERE id = ?',
                        (new_cat, new_desc, txn_dict['id'])
                    )
                    updated += 1
                break
    conn.commit()
    conn.close()
    return updated


# ==============================================================
# BUDGET FUNCTIONS
# ==============================================================

def set_budget(category, amount, month=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO budgets (category, amount, month) VALUES (?, ?, ?)',
        (category, amount, month)
    )
    conn.commit()
    conn.close()


def get_budgets(month=None):
    conn = get_connection()
    cursor = conn.cursor()
    if month:
        cursor.execute('''
            SELECT b1.category, b1.amount, b1.month FROM budgets b1 WHERE b1.month = ?
            UNION ALL
            SELECT b2.category, b2.amount, b2.month FROM budgets b2
            WHERE b2.month IS NULL
            AND b2.category NOT IN (SELECT category FROM budgets WHERE month = ?)
        ''', (month, month))
    else:
        cursor.execute('SELECT * FROM budgets WHERE month IS NULL ORDER BY category')
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_budget(category, month=None):
    conn = get_connection()
    cursor = conn.cursor()
    if month:
        cursor.execute('DELETE FROM budgets WHERE category = ? AND month = ?', (category, month))
    else:
        cursor.execute('DELETE FROM budgets WHERE category = ? AND month IS NULL', (category,))
    conn.commit()
    conn.close()


def get_spending_by_category_for_month(month):
    """Get actual spending per category for a given month (YYYY-MM)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, SUM(ABS(amount)) as total
        FROM transactions WHERE amount < 0 AND date LIKE ?
        GROUP BY category
    ''', (month + '%',))
    rows = cursor.fetchall()
    conn.close()
    return {r['category']: r['total'] for r in rows}


def get_avg_spending_by_category():
    """
    Get average monthly spending per category across all months with data.
    Returns: { 'Food & Drink': {'avg': 450.00, 'months': 3, 'total': 1350.00}, ... }
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all months with spending
    cursor.execute('''
        SELECT DISTINCT substr(date, 1, 7) as month
        FROM transactions WHERE amount < 0
        ORDER BY month
    ''')
    months = [r['month'] for r in cursor.fetchall()]

    if not months:
        conn.close()
        return {}

    # Get spending per category per month
    cursor.execute('''
        SELECT category, substr(date, 1, 7) as month, SUM(ABS(amount)) as total
        FROM transactions WHERE amount < 0
        GROUP BY category, month
    ''')
    rows = cursor.fetchall()
    conn.close()

    # Aggregate
    cat_data = {}
    for r in rows:
        cat = r['category']
        if cat not in cat_data:
            cat_data[cat] = {'months': set(), 'total': 0}
        cat_data[cat]['months'].add(r['month'])
        cat_data[cat]['total'] += r['total']

    result = {}
    for cat, data in cat_data.items():
        num_months = len(data['months'])
        result[cat] = {
            'avg': round(data['total'] / num_months, 2),
            'months': num_months,
            'total': round(data['total'], 2)
        }

    return result


def get_monthly_spending_history(num_months=6):
    """
    Get spending by category for the last N months.
    Returns: { 'Food & Drink': {'2024-01': 400, '2024-02': 500, ...}, ... }
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, substr(date, 1, 7) as month, SUM(ABS(amount)) as total
        FROM transactions WHERE amount < 0
        GROUP BY category, month
        ORDER BY month DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for r in rows:
        cat = r['category']
        if cat not in result:
            result[cat] = {}
        result[cat][r['month']] = round(r['total'], 2)

    return result


if __name__ == '__main__':
    initialize_database()
    print(f"Database created at: {DATABASE_PATH}")
