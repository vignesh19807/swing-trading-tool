import yfinance as yf
import pandas as pd


# ============================================================
# INITIAL STOCK UNIVERSE
# ============================================================
STOCKS = {
    "INFY.NS": "Infosys",
    "TCS.NS": "Tata Consultancy Services",
    "WIPRO.NS": "Wipro",
    "RELIANCE.NS": "Reliance Industries",
    "HDFCBANK.NS": "HDFC Bank",
    "ITC.NS": "ITC",
}


# ============================================================
# FETCH HISTORICAL DATA
# ============================================================

def fetch_stock_data(symbol):

    print(f"\nDownloading {symbol}...")

    ticker = yf.Ticker(symbol)

    data = ticker.history(
        period="2y",
        interval="1d",
        auto_adjust=False
    )

    if data.empty:
        print(f"WARNING: No data received for {symbol}")
        return None

    # Convert index into a normal column
    data = data.reset_index()

    # Keep only the fields required by our database
    data = data[
        [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Adj Close"
        ]
    ]

    # Standardize column names
    data.columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close"
    ]

    return data


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("==========================================")
    print("YFINANCE DATA COLLECTION TEST")
    print("==========================================")

    for symbol, company_name in STOCKS.items():

        data = fetch_stock_data(symbol)

        if data is None:
            continue

        print(
            f"{company_name}: "
            f"{len(data)} records"
        )

        print(
            f"Date range: "
            f"{data['date'].min()} → "
            f"{data['date'].max()}"
        )

        print("\nFirst 3 records:")
        print(data.head(3).to_string(index=False))

        print("\nLast 3 records:")
        print(data.tail(3).to_string(index=False))

        print("------------------------------------------")


if __name__ == "__main__":
    main()