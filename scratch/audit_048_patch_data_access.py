with open('backend/data_pipeline/backtest_data_access_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_get_input = """def get_backtest_input(symbol: str, evaluation_date: str, reporting_lag_days: int = 45) -> Optional[Dict[str, Any]]:"""
new_get_input = """def get_backtest_input(symbol: str, evaluation_date: str, reporting_lag_days: int = 45, filter_synthetic_holidays: bool = False) -> Optional[Dict[str, Any]]:"""

if old_get_input in text:
    text = text.replace(old_get_input, new_get_input, 1)

old_build_call_1 = """    df = build_backtesting_dataset(
        symbol=symbol_clean,
        start_date=date_clean,
        end_date=date_clean,
        reporting_lag_days=reporting_lag_days,
    )"""

new_build_call_1 = """    df = build_backtesting_dataset(
        symbol=symbol_clean,
        start_date=date_clean,
        end_date=date_clean,
        reporting_lag_days=reporting_lag_days,
        filter_synthetic_holidays=filter_synthetic_holidays,
    )"""

if old_build_call_1 in text:
    text = text.replace(old_build_call_1, new_build_call_1, 1)

old_get_inputs = """def get_backtest_inputs(symbol: str, start_date: str, end_date: str, reporting_lag_days: int = 45) -> List[Dict[str, Any]]:"""
new_get_inputs = """def get_backtest_inputs(symbol: str, start_date: str, end_date: str, reporting_lag_days: int = 45, filter_synthetic_holidays: bool = False) -> List[Dict[str, Any]]:"""

if old_get_inputs in text:
    text = text.replace(old_get_inputs, new_get_inputs, 1)

old_build_call_2 = """    df = build_backtesting_dataset(
        symbol=symbol_clean,
        start_date=start_clean,
        end_date=end_clean,
        reporting_lag_days=reporting_lag_days,
    )"""

new_build_call_2 = """    df = build_backtesting_dataset(
        symbol=symbol_clean,
        start_date=start_clean,
        end_date=end_clean,
        reporting_lag_days=reporting_lag_days,
        filter_synthetic_holidays=filter_synthetic_holidays,
    )"""

if old_build_call_2 in text:
    text = text.replace(old_build_call_2, new_build_call_2, 1)

with open('backend/data_pipeline/backtest_data_access_service.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully updated backtest_data_access_service.py with filter_synthetic_holidays parameter")

