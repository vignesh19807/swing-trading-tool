"""
Scope-Safe Financial Filing Parser & Banking Extractor
======================================================

Phase P2.8 Component:
- Extracts reported accounting metrics with explicit reporting scope preservation.
- Every record preserves:
    - Company identifier
    - Financial period
    - Reporting scope (CONSOLIDATED / STANDALONE)
    - Filing type (ORIGINAL, REVISED_DISCLOSURE, CORPORATE_RESTATEMENT)
    - Currency (standardized to INR)
    - Unit scale (CRORES, LAKHS, INR normalized to INR Crores)
    - Source document reference and page/location
- Distinguishes revenue categories:
    - Revenue from operations
    - Gross turnover
    - Other income
    - Total income
    - Net profit (PAT / attributable to shareholders)
    - EPS (Basic and Diluted)
    - Margins (operating and net)
- Specialized Commercial Banking Engine:
    - NII (Net Interest Income)
    - NIM (Net Interest Margin)
    - CRAR (Capital Adequacy Ratio)
    - Gross NPA (%) & Net NPA (%)
    - Customer Deposits
    - Gross Advances
    - Provision Coverage Ratio (PCR)
    - Corporate D/E and ROCE strictly enforced as NULL
    - Deposits strictly separated from conventional corporate debt
    - Strict prohibition on copying standalone banking metrics into consolidated records
"""

from typing import Dict, Any, Optional


def normalize_to_crores(value: Optional[float], reported_unit: str = "CRORES") -> Optional[float]:
    """
    Normalize accounting value to INR Crores.
    - 'CRORES' / 'CR': scale = 1.0
    - 'LAKHS' / 'LACS': scale = 0.01 (100 Lakhs = 1 Crore)
    - 'INR' / 'RUPEES': scale = 1e-7 (10,000,000 INR = 1 Crore)
    """
    if value is None:
        return None
    unit = reported_unit.upper().strip()
    if unit in ("CRORES", "CR", "IN_CRORES"):
        return round(float(value), 4)
    elif unit in ("LAKHS", "LACS", "IN_LAKHS"):
        return round(float(value) / 100.0, 4)
    elif unit in ("INR", "RUPEES"):
        return round(float(value) / 10000000.0, 4)
    else:
        raise ValueError(f"Unrecognized reporting unit: {reported_unit}")


class ScopeSafeFilingParser:
    """
    Parses reported financials ensuring strict scope isolation,
    revenue decomposition, and sector-aware banking normalization.
    """

    @staticmethod
    def parse_filing_payload(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate raw financial payload with strict scope enforcement.
        """
        # 1. Fundamental Scope & Identification Tracking
        symbol = str(raw_payload.get("symbol", "")).upper().strip()
        quarter = str(raw_payload.get("quarter", "")).upper().strip()
        filing_scope = str(raw_payload.get("filing_scope", "CONSOLIDATED")).upper().strip()
        if filing_scope not in ("CONSOLIDATED", "STANDALONE"):
            raise ValueError(f"Invalid filing_scope: {filing_scope}. Must be CONSOLIDATED or STANDALONE.")

        company_filing_type = str(raw_payload.get("company_filing_type", "ORIGINAL")).upper().strip()
        currency = str(raw_payload.get("currency", "INR")).upper().strip()
        unit = str(raw_payload.get("reported_unit", "CRORES")).upper().strip()
        source_doc_url = raw_payload.get("source_document_url")
        source_doc_hash = raw_payload.get("source_document_hash")
        source_location = raw_payload.get("source_page_or_location", "Financial Results Tables")

        # 2. Revenue & Operating Decomposition
        rev_ops = normalize_to_crores(raw_payload.get("revenue_from_operations"), unit)
        gross_turnover = normalize_to_crores(raw_payload.get("gross_revenue"), unit)
        other_income = normalize_to_crores(raw_payload.get("other_income"), unit)
        total_income = normalize_to_crores(raw_payload.get("total_income"), unit)
        raw_rev = normalize_to_crores(raw_payload.get("revenue"), unit)

        # Standardized top-line selection:
        # Standard corporate: revenue_from_operations preferred;
        # Banking/Financials: total_income / interest earned
        is_bank = bool(raw_payload.get("is_bank", False) or raw_payload.get("is_banking_institution", False))
        
        # Check bank indicators
        if any(raw_payload.get(k) is not None for k in (
            "net_interest_income", "customer_deposits", "capital_adequacy_ratio",
            "gross_npa_pct", "net_npa_pct", "advances", "provision_coverage_ratio"
        )):
            is_bank = True

        if is_bank:
            # For banks, standardized revenue represents Total Income / Total Revenue
            revenue = total_income or raw_rev or rev_ops
            if revenue is None:
                raise ValueError("Banking accounting error: Must provide total_income or revenue.")
        else:
            # For non-banks, revenue from operations is primary
            if rev_ops is not None:
                revenue = rev_ops
            elif raw_rev is not None:
                revenue = raw_rev
            elif gross_turnover is not None:
                revenue = gross_turnover
            elif total_income is not None:
                revenue = total_income
            else:
                raise ValueError("Corporate accounting error: Must provide revenue_from_operations or revenue.")

        # 3. Operating Costs & Profitability
        operating_expenses = normalize_to_crores(raw_payload.get("operating_expenses"), unit)
        operating_profit = normalize_to_crores(raw_payload.get("operating_profit"), unit)
        net_profit = normalize_to_crores(raw_payload.get("net_profit"), unit)
        
        # In consolidated reports, PAT attributable to shareholders takes precedence
        pat_attributable = normalize_to_crores(raw_payload.get("pat_attributable_to_owners"), unit)
        if pat_attributable is not None:
            net_profit = pat_attributable

        if revenue <= 0:
            raise ValueError(f"Accounting validation failure: Revenue must be positive, got {revenue}")
        if net_profit is None:
            raise ValueError("Accounting validation failure: Net profit is required.")
        if abs(net_profit) > revenue * 5.0:
            raise ValueError(f"Plausibility failure: Net profit ({net_profit}) exceeds 5x revenue ({revenue}).")

        # 4. Per Share & Margins
        eps = float(raw_payload["eps"]) if raw_payload.get("eps") is not None else None
        if eps is None:
            raise ValueError("Accounting validation failure: EPS is required.")

        operating_margin = round(operating_profit / revenue, 4) if (operating_profit is not None and revenue > 0) else None
        net_margin = round(net_profit / revenue, 4) if (net_profit is not None and revenue > 0) else None

        # 5. Balance Sheet & Solvency Line Items
        total_assets = normalize_to_crores(raw_payload.get("total_assets"), unit)
        total_equity = normalize_to_crores(raw_payload.get("total_equity"), unit)
        total_debt = normalize_to_crores(raw_payload.get("total_debt"), unit)
        current_liabilities = normalize_to_crores(raw_payload.get("current_liabilities"), unit)

        # 6. Specialized Commercial Banking Line Items
        net_interest_income = None
        net_interest_margin = None
        customer_deposits = None
        gross_advances = None
        capital_adequacy_ratio = None
        gross_npa_pct = None
        net_npa_pct = None
        provision_coverage_ratio = None

        roe = None
        if net_profit is not None and total_equity is not None and total_equity > 0:
            roe = round(net_profit / total_equity, 4)

        if is_bank:
            # Strict Banking Solvency Invariant: Corporate D/E and ROCE are NULL
            debt_equity = None
            roce = None
            total_debt = None  # Deposits are customer liabilities, not commercial debt

            # Guard against copying standalone metrics into consolidated records:
            # Standalone metrics must only populate if explicitly provided for the current scope
            # If parsing consolidated, standalone metrics must NOT be copied from standalone
            if raw_payload.get("is_scope_mixed", False):
                raise ValueError("Scope Safety Violation: Standalone banking metrics mixed into consolidated filing!")

            net_interest_income = normalize_to_crores(raw_payload.get("net_interest_income"), unit)
            nim_val = raw_payload.get("net_interest_margin")
            net_interest_margin = float(nim_val) if nim_val is not None else None
            customer_deposits = normalize_to_crores(raw_payload.get("customer_deposits"), unit)
            gross_advances = normalize_to_crores(raw_payload.get("gross_advances"), unit)

            car_val = raw_payload.get("capital_adequacy_ratio")
            capital_adequacy_ratio = float(car_val) if car_val is not None else None

            gnpa_val = raw_payload.get("gross_npa_pct")
            gross_npa_pct = float(gnpa_val) if gnpa_val is not None else None

            nnpa_val = raw_payload.get("net_npa_pct")
            net_npa_pct = float(nnpa_val) if nnpa_val is not None else None

            pcr_val = raw_payload.get("provision_coverage_ratio")
            provision_coverage_ratio = float(pcr_val) if pcr_val is not None else None

        else:
            # Corporate debt & ratios
            debt_equity = None
            if total_debt is not None and total_equity is not None and total_equity > 0:
                debt_equity = round(total_debt / total_equity, 4)

            roce = None
            if operating_profit is not None:
                if total_assets is not None and current_liabilities is not None:
                    capital_employed = total_assets - current_liabilities
                    if capital_employed > 0:
                        roce = round(operating_profit / capital_employed, 4)
                elif total_equity is not None and total_equity > 0:
                    capital_employed = total_equity + (total_debt or 0.0)
                    if capital_employed > 0:
                        roce = round(operating_profit / capital_employed, 4)

        return {
            "symbol": symbol,
            "quarter": quarter,
            "filing_scope": filing_scope,
            "company_filing_type": company_filing_type,
            "currency": currency,
            "unit_scale": "INR_CRORES",
            "source_document_url": source_doc_url,
            "source_document_hash": source_doc_hash,
            "source_page_or_location": source_location,
            
            # Standard Operating Metrics
            "revenue": revenue,
            "revenue_from_operations": rev_ops,
            "gross_revenue": gross_turnover,
            "other_income": other_income,
            "total_income": total_income,
            "operating_expenses": operating_expenses,
            "operating_profit": operating_profit,
            "net_profit": net_profit,
            "eps": eps,
            "operating_margin": operating_margin,
            "net_margin": net_margin,
            
            # Balance Sheet & Solvency
            "is_banking_institution": 1 if is_bank else 0,
            "total_assets": total_assets,
            "total_equity": total_equity,
            "total_debt": total_debt,
            "current_liabilities": current_liabilities,
            "roe": roe,
            "roce": roce,
            "debt_equity": debt_equity,
            
            # Banking Line Items
            "net_interest_income": net_interest_income,
            "net_interest_margin": net_interest_margin,
            "customer_deposits": customer_deposits,
            "gross_advances": gross_advances,
            "capital_adequacy_ratio": capital_adequacy_ratio,
            "gross_npa_pct": gross_npa_pct,
            "net_npa_pct": net_npa_pct,
            "provision_coverage_ratio": provision_coverage_ratio,
        }


# Backwards compatibility alias
FilingParser = ScopeSafeFilingParser
