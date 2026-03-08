"""
American Express CSV Parser — YOUR FIRST CHALLENGE

This parser is partially built. Your job is to finish it!

HOW AMEX CSVs WORK:
- Amex exports have columns: Date, Description, Amount
- Date format: MM/DD/YYYY
- Amounts: POSITIVE numbers = purchases (money you spent)
           NEGATIVE numbers = payments/credits
- This is the OPPOSITE of how we store them, so you need to flip the sign

STEPS:
1. Download a CSV from your Amex account (or use the sample data)
2. Open it in a text editor to see the exact column names
3. Fill in the parse() method below using chase.py as your reference
4. Test it by running: python -c "from parsers.amex import AmexParser; print('Import works!')"

HINT: Look at ChaseCreditParser — Amex works very similarly since
both are credit cards with positive amounts for purchases.
"""

from parsers.base import BaseParser


class AmexParser(BaseParser):
    """Parser for American Express CSV exports."""

    institution_name = "amex"
    account_type = "credit_card"

    def parse(self, csv_text):
        """
        Parse an Amex CSV into standardized transactions.

        YOUR TASK: Fill this in!

        Steps:
        1. Use self.read_csv_rows(csv_text) to get the rows
        2. Loop through each row
        3. For each row, create a transaction dict with:
           - 'date': use self.standardize_date() on the date column
           - 'description': the description column, stripped of whitespace
           - 'amount': the amount as a float, WITH THE SIGN FLIPPED
           - 'category': 'Uncategorized' for now (or copy the guess_category method from chase.py)
        4. Append each transaction to a list and return it
        """
        rows = self.read_csv_rows(csv_text)
        transactions = []

        # ------- YOUR CODE GOES HERE -------
        # Use the Chase parser as your reference!
        # Remember: Amex amounts need their sign flipped
        #   purchases are positive in the CSV but should be negative in our system
        #   payments are negative in the CSV but should be positive in our system

        pass  # Remove this line when you add your code

        # ------- END YOUR CODE -------

        return transactions
