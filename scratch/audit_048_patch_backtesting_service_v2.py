with open('backend/data_pipeline/backtesting_dataset_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_def = """def build_backtesting_dataset(
    symbol: str,
    start_date: str,
    end_date: str,
    reporting_lag_days: int = 45,
) -> pd.DataFrame:"""

new_def = """def build_backtesting_dataset(
    symbol: str,
    start_date: str,
    end_date: str,
    reporting_lag_days: int = 45,
    filter_synthetic_holidays: bool = False,
) -> pd.DataFrame:"""

assert old_def in text, "old_def not found in backtesting_dataset_service.py"
text = text.replace(old_def, new_def, 1)

old_market_call = """    market_result = get_historical_data(
        symbol,
        start_date=start_date,
        end_date=end_date,
        include_adjusted_close=True,
    )"""

new_market_call = """    market_result = get_historical_data(
        symbol,
        start_date=start_date,
        end_date=end_date,
        include_adjusted_close=True,
        filter_synthetic_holidays=filter_synthetic_holidays,
    )"""

assert old_market_call in text, "old_market_call not found in backtesting_dataset_service.py"
text = text.replace(old_market_call, new_market_call, 1)

with open('backend/data_pipeline/backtesting_dataset_service.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully replaced build_backtesting_dataset definition and call")

