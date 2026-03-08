"""
Base parser that all institution-specific parsers inherit from.

WHAT YOU'LL LEARN HERE:
- Python classes and inheritance
- Abstract methods (methods that subclasses MUST implement)
- A common pattern called the "Template Method" pattern

Every bank exports CSVs differently. This base class defines WHAT a parser
must do, and each bank-specific parser defines HOW to do it.
"""

from abc import ABC, abstractmethod
import csv
from io import StringIO


class BaseParser(ABC):
    """
    Abstract base class for CSV parsers.

    Every parser must implement the `parse()` method, which takes raw CSV text
    and returns a list of standardized transaction dictionaries.

    Each transaction dict looks like:
    {
        "date": "2024-01-15",         # YYYY-MM-DD format (standardized)
        "description": "AMAZON.COM",   # What the transaction was
        "amount": -52.99,             # Negative = money out, Positive = money in
        "category": "Shopping"         # Optional, defaults to "Uncategorized"
    }
    """

    # Each subclass sets these
    institution_name = "unknown"
    account_type = "unknown"  # "checking", "credit_card", "brokerage", etc.

    @abstractmethod
    def parse(self, csv_text):
        """
        Parse raw CSV text into a list of standardized transaction dicts.

        Args:
            csv_text: String containing the full CSV file contents

        Returns:
            List of dicts, each with keys: date, description, amount, category
        """
        pass

    def read_csv_rows(self, csv_text):
        """
        Helper method: converts raw CSV text into a list of dictionaries.
        Each dict represents one row, with column headers as keys.

        This handles the boring part so your parse() method can focus on
        mapping the bank's column names to our standardized format.

        Example:
            If the CSV has headers: Date, Description, Amount
            This returns: [{"Date": "01/15/2024", "Description": "AMAZON", "Amount": "-52.99"}, ...]
        """
        reader = csv.DictReader(StringIO(csv_text))
        return list(reader)

    def standardize_date(self, date_string, input_format="%m/%d/%Y"):
        """
        Convert a date string to our standard YYYY-MM-DD format.

        Most banks use MM/DD/YYYY, but some use other formats.
        Override input_format in your parser if needed.

        Example:
            standardize_date("01/15/2024") → "2024-01-15"
        """
        from datetime import datetime
        parsed = datetime.strptime(date_string, input_format)
        return parsed.strftime("%Y-%m-%d")
