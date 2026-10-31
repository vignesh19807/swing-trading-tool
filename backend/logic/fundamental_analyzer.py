"""
Fundamental Analyzer Facade
===========================

Unified interface for fundamental financial sub-analyzers:
- analyze_roe
- analyze_roce
- analyze_debt_equity
- analyze_profit_margin
- analyze_growth

Each analyzer accepts:
    symbol: str
    evaluation_date: Optional[str] = None

When evaluation_date is provided, only quarterly financial records published
or eligible as of that date (via verified publication date or 45-day fallback lag)
are analyzed. When evaluation_date is None, the latest current database snapshot is used.
"""

from typing import Optional, Dict, Any

from backend.logic.roe_analyzer import analyze_roe
from backend.logic.roce_analyzer import analyze_roce
from backend.logic.debt_equity_analyzer import analyze_debt_equity
from backend.logic.profit_margin_analyzer import analyze_profit_margin
from backend.logic.growth_analyzer import analyze_growth

__all__ = [
    "analyze_roe",
    "analyze_roce",
    "analyze_debt_equity",
    "analyze_profit_margin",
    "analyze_growth",
]

