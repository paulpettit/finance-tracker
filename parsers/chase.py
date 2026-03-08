"""
Chase CSV Parser — YOUR REFERENCE IMPLEMENTATION

This is a fully working parser for Chase checking/credit card exports.
Study this one, then use it as a template to build the others.

HOW CHASE CSVs WORK:
- Chase checking exports have columns: Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
- Chase credit card exports have columns: Transaction Date, Post Date, Description, Category, Type, Amount, Memo
- Amounts: negative = purchase/debit, positive = payment/credit (for credit cards, this is reversed)

WHAT YOU'LL LEARN:
- How to implement a parser by extending BaseParser
- How to handle the quirks of a specific bank's export format
- How to map their columns to our standardized format
"""

from parsers.base import BaseParser


class ChaseCheckingParser(BaseParser):
    """Parser for Chase checking account CSV exports."""

    institution_name = "chase"
    account_type = "checking"

    def parse(self, csv_text):
        """
        Parse a Chase checking CSV into standardized transactions.

        Chase checking columns:
            Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
        """
        rows = self.read_csv_rows(csv_text)
        transactions = []

        for row in rows:
            # Skip empty rows
            if not row.get('Posting Date') or not row.get('Amount'):
                continue

            transaction = {
                'date': self.standardize_date(row['Posting Date']),
                'description': row['Description'].strip(),
                'amount': float(row['Amount']),
                'category': self.guess_category(row['Description'])
            }
            transactions.append(transaction)

        return transactions

    def guess_category(self, description):
        """
        Simple keyword-based categorization.

        YOUR TASK: Expand this! Add more keywords and categories.
        Later, you could even use AI to categorize transactions.

        Hint: Think about your own spending — what merchants show up
        most often on your Chase statement?
        """
        description = description.upper()

        # Each tuple is (keyword_to_look_for, category_to_assign)
        category_rules = [
            ('AMAZON', 'Shopping'),
            ('WALMART', 'Shopping'),
            ('TARGET', 'Shopping'),
            ('UBER EATS', 'Food & Drink'),
            ('DOORDASH', 'Food & Drink'),
            ('GRUBHUB', 'Food & Drink'),
            ('STARBUCKS', 'Food & Drink'),
            ('MCDONALD', 'Food & Drink'),
            ('CHIPOTLE', 'Food & Drink'),
            ('NETFLIX', 'Subscriptions'),
            ('SPOTIFY', 'Subscriptions'),
            ('HULU', 'Subscriptions'),
            ('UBER TRIP', 'Transportation'),
            ('LYFT', 'Transportation'),
            ('SHELL', 'Transportation'),
            ('CHEVRON', 'Transportation'),
            ('RENT', 'Housing'),
            ('MORTGAGE', 'Housing'),
            ('ELECTRIC', 'Utilities'),
            ('WATER', 'Utilities'),
            ('GAS BILL', 'Utilities'),
            ('TRANSFER', 'Transfer'),
            ('ZELLE', 'Transfer'),
            ('VENMO', 'Transfer'),
            ('PAYROLL', 'Income'),
            ('DIRECT DEP', 'Income'),
            ('DEPOSIT', 'Income'),
        ]

        for keyword, category in category_rules:
            if keyword in description:
                return category

        return 'Uncategorized'


class ChaseCreditParser(BaseParser):
    """Parser for Chase credit card CSV exports."""

    institution_name = "chase"
    account_type = "credit_card"

    def parse(self, csv_text):
        """
        Parse a Chase credit card CSV into standardized transactions.

        Chase credit card columns:
            Transaction Date, Post Date, Description, Category, Type, Amount, Memo

        NOTE: Chase credit cards use POSITIVE amounts for purchases and
        NEGATIVE for payments/credits. We flip this to match our standard:
        negative = money spent, positive = money received.
        """
        rows = self.read_csv_rows(csv_text)
        transactions = []

        for row in rows:
            if not row.get('Transaction Date') or not row.get('Amount'):
                continue

            # Chase credit card amounts are opposite of what we want
            # They show purchases as positive, we want them as negative
            raw_amount = float(row['Amount'])
            amount = -raw_amount  # Flip the sign

            transaction = {
                'date': self.standardize_date(row['Transaction Date']),
                'description': row['Description'].strip(),
                'amount': amount,
                # Chase credit cards actually include a Category column!
                'category': row.get('Category', 'Uncategorized').strip()
            }
            transactions.append(transaction)

        return transactions
