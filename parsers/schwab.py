"""
Charles Schwab CSV Parser — TODO
Schwab exports vary by account type (brokerage, checking).
Download one to see the format.
"""
from parsers.base import BaseParser

class SchwabParser(BaseParser):
    institution_name = "schwab"
    account_type = "brokerage"

    def parse(self, csv_text):
        raise NotImplementedError("Schwab parser not yet implemented")
