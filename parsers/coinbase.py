"""
Coinbase CSV Parser — TODO
Coinbase exports: Timestamp, Transaction Type, Asset, Quantity Transacted, Spot Price, Subtotal, Total, Fees, Notes
"""
from parsers.base import BaseParser

class CoinbaseParser(BaseParser):
    institution_name = "coinbase"
    account_type = "crypto"

    def parse(self, csv_text):
        raise NotImplementedError("Coinbase parser not yet implemented")
