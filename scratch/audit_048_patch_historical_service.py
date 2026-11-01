with open('backend/data_pipeline/historical_data_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_target = """from backend.data_pipeline.data_service import (
    get_stock_data,
    get_stock_data_with_adjusted_close,
)"""

new_replacement = """from backend.data_pipeline.data_service import (
    get_stock_data,
    get_stock_data_with_adjusted_close,
)
from backend.data_pipeline.research_market_data_filter import filter_research_market_data"""

if old_target in text:
    text = text.replace(old_target, new_replacement, 1)

old_def = """def get_historical_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_adjusted_close: bool = False,
) -> dict:"""

new_def = """def get_historical_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_adjusted_close: bool = False,
    filter_synthetic_holidays: bool = False,
) -> dict:"""

if old_def in text:
    text = text.replace(old_def, new_def, 1)

old_sort = '    data = data.sort_values("date").reset_index(drop=True)'

new_sort = """    data = data.sort_values("date").reset_index(drop=True)

    if filter_synthetic_holidays:
        data = filter_research_market_data(
            data,
            exclude_synthetic_holidays=True,
            exclude_stale_flat_bars=False,
            exclude_anomalies=False
        ).reset_index(drop=True)"""

if old_sort in text:
    text = text.replace(old_sort, new_sort, 1)

with open('backend/data_pipeline/historical_data_service.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully updated historical_data_service.py")

