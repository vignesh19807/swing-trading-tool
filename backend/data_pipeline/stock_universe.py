"""
Stock Universe
==============
Central source of truth for the initial 50-stock universe
used by the Swing Trading Intelligence Platform.

Universe basis:
- Nifty 50 constituents
- NSE-listed equities
- Current development universe as of August 2026

Note:
Wipro remains in the current universe for now. NSE has announced
that BSE will replace Wipro in Nifty 50 effective September 30, 2026.
"""

from collections import Counter


# ============================================================
# 50-STOCK UNIVERSE
# ============================================================

STOCK_UNIVERSE = [

    # --------------------------------------------------------
    # FINANCIAL SERVICES
    # --------------------------------------------------------

    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks",
        "exchange": "NSE",
    },

    {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks",
        "exchange": "NSE",
    },

    {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "sector": "Financial Services",
        "industry": "Banks",
        "exchange": "NSE",
    },

    {
        "symbol": "AXISBANK",
        "name": "Axis Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks",
        "exchange": "NSE",
    },

    {
        "symbol": "KOTAKBANK",
        "name": "Kotak Mahindra Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks",
        "exchange": "NSE",
    },

    {
        "symbol": "BAJFINANCE",
        "name": "Bajaj Finance Limited",
        "sector": "Financial Services",
        "industry": "Consumer Finance",
        "exchange": "NSE",
    },

    {
        "symbol": "BAJAJFINSV",
        "name": "Bajaj Finserv Limited",
        "sector": "Financial Services",
        "industry": "Financial Services",
        "exchange": "NSE",
    },

    {
        "symbol": "SHRIRAMFIN",
        "name": "Shriram Finance Limited",
        "sector": "Financial Services",
        "industry": "Finance",
        "exchange": "NSE",
    },

    {
        "symbol": "JIOFIN",
        "name": "Jio Financial Services Limited",
        "sector": "Financial Services",
        "industry": "Financial Services",
        "exchange": "NSE",
    },

    {
        "symbol": "SBILIFE",
        "name": "SBI Life Insurance Company Limited",
        "sector": "Financial Services",
        "industry": "Life Insurance",
        "exchange": "NSE",
    },

    {
        "symbol": "HDFCLIFE",
        "name": "HDFC Life Insurance Company Limited",
        "sector": "Financial Services",
        "industry": "Life Insurance",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # INFORMATION TECHNOLOGY
    # --------------------------------------------------------

    {
        "symbol": "TCS",
        "name": "Tata Consultancy Services Limited",
        "sector": "Information Technology",
        "industry": "IT Services",
        "exchange": "NSE",
    },

    {
        "symbol": "INFY",
        "name": "Infosys Limited",
        "sector": "Information Technology",
        "industry": "IT Services",
        "exchange": "NSE",
    },

    {
        "symbol": "HCLTECH",
        "name": "HCL Technologies Limited",
        "sector": "Information Technology",
        "industry": "IT Services",
        "exchange": "NSE",
    },

    {
        "symbol": "TECHM",
        "name": "Tech Mahindra Limited",
        "sector": "Information Technology",
        "industry": "IT Services",
        "exchange": "NSE",
    },

    {
        "symbol": "WIPRO",
        "name": "Wipro Limited",
        "sector": "Information Technology",
        "industry": "IT Services",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # ENERGY / OIL & GAS
    # --------------------------------------------------------

    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Limited",
        "sector": "Oil, Gas & Consumable Fuels",
        "industry": "Oil & Gas",
        "exchange": "NSE",
    },

    {
        "symbol": "ONGC",
        "name": "Oil and Natural Gas Corporation Limited",
        "sector": "Oil, Gas & Consumable Fuels",
        "industry": "Oil & Gas Exploration & Production",
        "exchange": "NSE",
    },

    {
        "symbol": "COALINDIA",
        "name": "Coal India Limited",
        "sector": "Oil, Gas & Consumable Fuels",
        "industry": "Coal",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # POWER / UTILITIES
    # --------------------------------------------------------

    {
        "symbol": "NTPC",
        "name": "NTPC Limited",
        "sector": "Power",
        "industry": "Power Generation",
        "exchange": "NSE",
    },

    {
        "symbol": "POWERGRID",
        "name": "Power Grid Corporation of India Limited",
        "sector": "Power",
        "industry": "Power Transmission",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # TELECOMMUNICATION
    # --------------------------------------------------------

    {
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel Limited",
        "sector": "Telecommunication",
        "industry": "Telecommunication Services",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # AUTOMOBILE
    # --------------------------------------------------------

    {
        "symbol": "M&M",
        "name": "Mahindra & Mahindra Limited",
        "sector": "Automobile and Auto Components",
        "industry": "Passenger Cars & Utility Vehicles",
        "exchange": "NSE",
    },

    {
        "symbol": "MARUTI",
        "name": "Maruti Suzuki India Limited",
        "sector": "Automobile and Auto Components",
        "industry": "Passenger Cars & Utility Vehicles",
        "exchange": "NSE",
    },

    {
        "symbol": "BAJAJ-AUTO",
        "name": "Bajaj Auto Limited",
        "sector": "Automobile and Auto Components",
        "industry": "Two Wheelers",
        "exchange": "NSE",
    },

    {
        "symbol": "EICHERMOT",
        "name": "Eicher Motors Limited",
        "sector": "Automobile and Auto Components",
        "industry": "Two Wheelers",
        "exchange": "NSE",
    },

    {
        "symbol": "HEROMOTOCO",
        "name": "Hero MotoCorp Limited",
        "sector": "Automobile and Auto Components",
        "industry": "Two Wheelers",
        "exchange": "NSE",
    },

    {
        "symbol": "TMPV",
        "name": "Tata Motors Passenger Vehicles Limited",
        "sector": "Automobile and Auto Components",
        "industry": "Passenger Cars & Utility Vehicles",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # FMCG / CONSUMER
    # --------------------------------------------------------

    {
        "symbol": "ITC",
        "name": "ITC Limited",
        "sector": "Fast Moving Consumer Goods",
        "industry": "Tobacco Products",
        "exchange": "NSE",
    },

    {
        "symbol": "HINDUNILVR",
        "name": "Hindustan Unilever Limited",
        "sector": "Fast Moving Consumer Goods",
        "industry": "Personal Care Products",
        "exchange": "NSE",
    },

    {
        "symbol": "NESTLEIND",
        "name": "Nestle India Limited",
        "sector": "Fast Moving Consumer Goods",
        "industry": "Packaged Foods",
        "exchange": "NSE",
    },

    {
        "symbol": "TATACONSUM",
        "name": "Tata Consumer Products Limited",
        "sector": "Fast Moving Consumer Goods",
        "industry": "Consumer Food Products",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # CONSUMER DURABLES
    # --------------------------------------------------------

    {
        "symbol": "TITAN",
        "name": "Titan Company Limited",
        "sector": "Consumer Durables",
        "industry": "Jewellery",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # CONSUMER SERVICES
    # --------------------------------------------------------

    {
        "symbol": "ETERNAL",
        "name": "Eternal Limited",
        "sector": "Consumer Services",
        "industry": "Internet & Digital Services",
        "exchange": "NSE",
    },

    {
        "symbol": "TRENT",
        "name": "Trent Limited",
        "sector": "Consumer Services",
        "industry": "Retail",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # PAINTS / CHEMICALS
    # --------------------------------------------------------

    {
        "symbol": "ASIANPAINT",
        "name": "Asian Paints Limited",
        "sector": "Consumer Durables",
        "industry": "Paints",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # METALS & MINING
    # --------------------------------------------------------

    {
        "symbol": "TATASTEEL",
        "name": "Tata Steel Limited",
        "sector": "Metals & Mining",
        "industry": "Steel",
        "exchange": "NSE",
    },

    {
        "symbol": "JSWSTEEL",
        "name": "JSW Steel Limited",
        "sector": "Metals & Mining",
        "industry": "Steel",
        "exchange": "NSE",
    },

    {
        "symbol": "HINDALCO",
        "name": "Hindalco Industries Limited",
        "sector": "Metals & Mining",
        "industry": "Aluminium",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # CAPITAL GOODS / DEFENCE
    # --------------------------------------------------------

    {
        "symbol": "BEL",
        "name": "Bharat Electronics Limited",
        "sector": "Capital Goods",
        "industry": "Aerospace & Defence",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # CONSTRUCTION / INFRASTRUCTURE
    # --------------------------------------------------------

    {
        "symbol": "LT",
        "name": "Larsen & Toubro Limited",
        "sector": "Construction",
        "industry": "Construction & Engineering",
        "exchange": "NSE",
    },

    {
        "symbol": "ULTRACEMCO",
        "name": "UltraTech Cement Limited",
        "sector": "Construction Materials",
        "industry": "Cement",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # ADANI GROUP
    # --------------------------------------------------------

    {
        "symbol": "ADANIENT",
        "name": "Adani Enterprises Limited",
        "sector": "Metals & Mining",
        "industry": "Diversified",
        "exchange": "NSE",
    },

    {
        "symbol": "ADANIPORTS",
        "name": "Adani Ports and Special Economic Zone Limited",
        "sector": "Services",
        "industry": "Ports & Logistics",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # PHARMACEUTICALS / HEALTHCARE
    # --------------------------------------------------------

    {
        "symbol": "SUNPHARMA",
        "name": "Sun Pharmaceutical Industries Limited",
        "sector": "Healthcare",
        "industry": "Pharmaceuticals",
        "exchange": "NSE",
    },

    {
        "symbol": "CIPLA",
        "name": "Cipla Limited",
        "sector": "Healthcare",
        "industry": "Pharmaceuticals",
        "exchange": "NSE",
    },

    {
        "symbol": "DRREDDY",
        "name": "Dr. Reddy's Laboratories Limited",
        "sector": "Healthcare",
        "industry": "Pharmaceuticals",
        "exchange": "NSE",
    },

    {
        "symbol": "APOLLOHOSP",
        "name": "Apollo Hospitals Enterprise Limited",
        "sector": "Healthcare",
        "industry": "Healthcare Services",
        "exchange": "NSE",
    },

    {
        "symbol": "MAXHEALTH",
        "name": "Max Healthcare Institute Limited",
        "sector": "Healthcare",
        "industry": "Healthcare Services",
        "exchange": "NSE",
    },


    # --------------------------------------------------------
    # DIVERSIFIED / INDUSTRIAL
    # --------------------------------------------------------

    {
        "symbol": "GRASIM",
        "name": "Grasim Industries Limited",
        "sector": "Diversified",
        "industry": "Diversified",
        "exchange": "NSE",
    },
]


# ============================================================
# VALIDATION
# ============================================================

REQUIRED_FIELDS = {
    "symbol",
    "name",
    "sector",
    "industry",
    "exchange",
}


def validate_stock_universe():
    """Validate the stock universe for basic data-quality issues."""

    print("\n==========================================")
    print("STOCK UNIVERSE VALIDATION")
    print("==========================================")

    # --------------------------------------------------------
    # Stock count
    # --------------------------------------------------------

    total_stocks = len(STOCK_UNIVERSE)

    print(f"Total stocks: {total_stocks}")

    # --------------------------------------------------------
    # Symbol validation
    # --------------------------------------------------------

    symbols = [
        stock["symbol"]
        for stock in STOCK_UNIVERSE
    ]

    symbol_counts = Counter(symbols)

    duplicate_symbols = sorted(
        symbol
        for symbol, count in symbol_counts.items()
        if count > 1
    )

    if duplicate_symbols:

        print(
            f"❌ Duplicate symbols: "
            f"{duplicate_symbols}"
        )

    else:

        print("✓ Duplicate symbols: 0")

    # --------------------------------------------------------
    # Missing field validation
    # --------------------------------------------------------

    missing_fields = []

    for stock in STOCK_UNIVERSE:

        missing = REQUIRED_FIELDS - set(stock.keys())

        if missing:

            missing_fields.append(
                {
                    "symbol": stock.get(
                        "symbol",
                        "UNKNOWN"
                    ),
                    "fields": sorted(missing),
                }
            )

    if missing_fields:

        print("❌ Missing fields:")

        for item in missing_fields:

            print(
                f"   {item['symbol']}: "
                f"{item['fields']}"
            )

    else:

        print("✓ Missing fields: 0")

    # --------------------------------------------------------
    # Empty value validation
    # --------------------------------------------------------

    empty_values = []

    for stock in STOCK_UNIVERSE:

        for field in REQUIRED_FIELDS:

            value = stock.get(field)

            if not value or not str(value).strip():

                empty_values.append(
                    (
                        stock.get(
                            "symbol",
                            "UNKNOWN"
                        ),
                        field,
                    )
                )

    if empty_values:

        print("❌ Empty values:")

        for symbol, field in empty_values:

            print(
                f"   {symbol}: {field}"
            )

    else:

        print("✓ Empty values: 0")

    # --------------------------------------------------------
    # Expected universe size
    # --------------------------------------------------------

    if total_stocks == 50:

        print("✓ Expected universe size: 50")

    else:

        print(
            f"❌ Expected 50 stocks, "
            f"found {total_stocks}"
        )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    passed = (
        total_stocks == 50
        and not duplicate_symbols
        and not missing_fields
        and not empty_values
    )

    print("------------------------------------------")

    if passed:

        print("🎉 STOCK UNIVERSE VALIDATION PASSED")

    else:

        print("⚠ STOCK UNIVERSE VALIDATION FAILED")

    print("==========================================\n")

    return passed


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    validate_stock_universe()