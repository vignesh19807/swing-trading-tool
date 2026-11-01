"""
Historical Universe & Corporate Action Metadata Schema
======================================================

Provides formal metadata schemas and models for:
1. Point-in-time index membership history (e.g. Nifty 50 additions and deletions)
2. Corporate actions tracking (stock splits, bonus issues, cash dividends, demergers)
3. Research universe disclosure tags (flagging survivorship-bias exposure)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class CorporateActionRecord:
    symbol: str
    action_type: str            # 'SPLIT', 'BONUS', 'DIVIDEND', 'DEMERGER'
    ex_date: str                # YYYY-MM-DD
    record_date: Optional[str]  # YYYY-MM-DD
    ratio: Optional[str]        # e.g. '1:1' for bonus, '10:1' for split
    cash_amount: Optional[float]# Dividend amount in INR
    adjustment_factor: float    # e.g. 0.5 for 2:1 split
    is_verified: bool = False
    source: str = "UNVERIFIED"  # 'NSE_OFFICIAL', 'BSE_OFFICIAL', 'ESTIMATED'
    notes: Optional[str] = None


@dataclass
class UniverseConstituentRecord:
    symbol: str
    company_name: str
    index_name: str             # e.g. 'NIFTY50', 'NIFTY_NEXT_50'
    effective_from: str         # YYYY-MM-DD
    effective_to: Optional[str] # YYYY-MM-DD (None if currently active)
    status: str                 # 'ACTIVE', 'REMOVED', 'MERGED', 'SUSPENDED'
    reason: Optional[str] = None# 'INDEX_REBALANCING', 'DEMERGER', 'DELISTING'


@dataclass
class ResearchUniverseMetadata:
    universe_id: str = "NIFTY50_FIXED_AUG2026"
    constituent_count: int = 52
    snapshot_date: str = "2026-08-01"
    is_survivorship_bias_free: bool = False
    bias_classification: str = "FIXED_SURVIVOR_SAMPLE"
    disclosed_limitations: List[str] = field(default_factory=lambda: [
        "Index constituents reflect August 2026 snapshot.",
        "Historical additions and deletions are not tracked point-in-time.",
        "Delisted or demoted historical constituents prior to 2026 are absent.",
        "Multi-year returns suffer from positive survivor bias."
    ])

    def get_disclosure_text(self) -> str:
        return (
            f"RESEARCH UNIVERSE DISCLOSURE [{self.universe_id}]: "
            f"Contains {self.constituent_count} equities. Survivorship-bias free: {self.is_survivorship_bias_free}. "
            f"Classification: {self.bias_classification}."
        )

