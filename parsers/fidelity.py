"""
Fidelity CSV Parser — TODO

Fidelity exports vary based on account type (401k, brokerage, HSA).
Download a CSV from Fidelity and open it in a text editor to see
the exact column names before building this parser.

Typical columns for a brokerage account:
    Run Date, Action, Symbol, Description, Type, Quantity, Price, Commission, Fees, Accrued Interest, Amount, Settlement Date

For investment accounts, you'll want to track:
- Buy/Sell transactions
- Dividends
- The symbol (stock ticker)

This is more complex than a bank parser — save it for Phase 2 or 3.
"""

from parsers.base import BaseParser


class FidelityParser(BaseParser):
    institution_name = "fidelity"
    account_type = "brokerage"

    def parse(self, csv_text):
        # TODO: Implement this parser
        # Download a Fidelity CSV first to see the exact format
        raise NotImplementedError("Fidelity parser not yet implemented")
