"""
Kite Connect Data Provider
===========================

Reserved for the Zerodha Kite Connect market-data provider.

Status:
    Prepared / Not yet connected.

The actual Kite API implementation will be added after
API credentials and authentication configuration are available.
"""


def fetch_stock_data(symbol, period="2y"):
    """
    Placeholder for Kite historical market-data retrieval.

    Kite API integration is intentionally not implemented yet.
    """

    raise NotImplementedError(
        "Kite provider is not connected yet. "
        "Use the yfinance provider for current development."
    )


def get_provider_name():
    """Return the provider name."""

    return "kite"