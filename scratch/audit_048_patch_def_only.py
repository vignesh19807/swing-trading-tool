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

assert old_def in text, "old_def not found"
text = text.replace(old_def, new_def, 1)

with open('backend/data_pipeline/backtesting_dataset_service.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully replaced build_backtesting_dataset header")

