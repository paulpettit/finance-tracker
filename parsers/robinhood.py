"""
Robinhood CSV Parser — TODO
Download your Robinhood transaction history to see the exact format.
"""
from parsers.base import BaseParser

class RobinhoodParser(BaseParser):
    institution_name = "robinhood"
    account_type = "brokerage"

    def parse(self, csv_text):
        raise NotImplementedError("Robinhood parser not yet implemented")
