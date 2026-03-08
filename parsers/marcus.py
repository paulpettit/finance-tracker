"""
Marcus (Goldman Sachs) CSV Parser — TODO
Marcus is a savings account, so transactions are mostly transfers and interest.
"""
from parsers.base import BaseParser

class MarcusParser(BaseParser):
    institution_name = "marcus"
    account_type = "savings"

    def parse(self, csv_text):
        raise NotImplementedError("Marcus parser not yet implemented")
