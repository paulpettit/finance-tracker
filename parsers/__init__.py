"""
Parser registry — maps institution names to their parser classes.

When you finish building a new parser, register it here so the app can find it.
"""

from parsers.chase import ChaseCheckingParser, ChaseCreditParser
# Uncomment these as you build each parser:
# from parsers.amex import AmexParser
# from parsers.fidelity import FidelityParser
# from parsers.coinbase import CoinbaseParser
# from parsers.robinhood import RobinhoodParser
# from parsers.marcus import MarcusParser
# from parsers.schwab import SchwabParser

# This dictionary maps a user-friendly name to the parser class
# The upload page will show these as dropdown options
PARSERS = {
    'chase_checking': ChaseCheckingParser(),
    'chase_credit': ChaseCreditParser(),
    # 'amex': AmexParser(),
    # 'fidelity': FidelityParser(),
    # 'coinbase': CoinbaseParser(),
    # 'robinhood': RobinhoodParser(),
    # 'marcus': MarcusParser(),
    # 'schwab': SchwabParser(),
}


def get_parser(institution_key):
    """
    Get a parser by its key. Returns None if not found.

    Usage:
        parser = get_parser('chase_checking')
        transactions = parser.parse(csv_text)
    """
    return PARSERS.get(institution_key)


def get_available_parsers():
    """Returns a list of (key, institution_name) tuples for the upload dropdown."""
    return [(key, parser.institution_name) for key, parser in PARSERS.items()]
