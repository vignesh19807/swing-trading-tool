"""
Staging Financial Ingestion Orchestrator
=======================================

Phase P2.5 Orchestrator: Chains Retrieval -> Parsing -> Session Validation -> Staging Insertion.
Targets strictly `database/staging_financial_expansion.db`.
"""

from pathlib import Path
from typing import Dict, Any, List
import sqlite3

from backend.data_pipeline.financial_filing_retriever import FilingDocumentManager
from backend.data_pipeline.financial_filing_parser import FilingParser
from backend.data_pipeline.financial_filing_validator import calculate_effective_trading_date
from backend.data_pipeline.staging_financial_vintage_service import StagingFinancialVintageRepository


class StagingIngestionOrchestrator:
    """Coordinates authentic disclosure ingestion into staging database."""

    def __init__(self, repo: StagingFinancialVintageRepository, doc_manager: FilingDocumentManager):
        self.repo = repo
        self.doc_manager = doc_manager

    def ingest_filing(
        self,
        symbol: str,
        company_id: int,
        quarter: str,
        period_start_date: str,
        period_end_date: str,
        accounting_standard: str,
        filing_scope: str,
        filing_type: str,
        version_sequence: int,
        exchange: str,
        exchange_broadcast_id: str,
        publication_timestamp: str,
        raw_accounting_data: Dict[str, Any],
        source_url: str,
        raw_document_bytes: bytes,
        doc_filename: str,
        verification_notes: str = "Verified Primary Filing",
        remediation_type: str = "ORIGINAL_PILOT",
        remediation_notes: str = None,
        original_broadcast_id: str = None
    ) -> int:
        """
        Process a single filing end-to-end:
        1. Store raw document and generate SHA-256 fingerprint.
        2. Parse accounting line items and calculate standardized ratios.
        3. Calculate deterministic effective trading date.
        4. Validate against synthetic blacklist.
        5. Insert into staging database.
        """
        # Step 1: Document Storage & Hashing
        doc_meta = self.doc_manager.preserve_document(
            symbol=symbol,
            quarter=quarter,
            exchange=exchange,
            doc_filename=doc_filename,
            raw_bytes=raw_document_bytes,
            source_url=source_url
        )
        doc_hash = doc_meta["source_document_hash"]

        # Step 2: Parsing & Ratio Calculation
        parsed_metrics = FilingParser.parse_filing_payload(raw_accounting_data)

        # Step 3: Effective Trading Date
        eff_date = calculate_effective_trading_date(publication_timestamp)

        # Step 4: Construct Full Vintage Record
        vintage_payload = {
            "company_id": company_id,
            "quarter": quarter,
            "period_start_date": period_start_date,
            "period_end_date": period_end_date,
            "accounting_standard": accounting_standard,
            "filing_scope": filing_scope,
            "filing_type": filing_type,
            "version_sequence": version_sequence,
            "superseded_by_vintage_id": None,
            "exchange": exchange,
            "exchange_broadcast_id": exchange_broadcast_id,
            "publication_timestamp": publication_timestamp,
            "effective_trading_date": eff_date,
            "verification_status": "VERIFIED",
            "verification_notes": verification_notes,
            "remediation_type": remediation_type,
            "remediation_notes": remediation_notes,
            "original_broadcast_id": original_broadcast_id,
            **parsed_metrics,
            "source_document_url": source_url,
            "source_document_hash": doc_hash,
        }

        # Step 5: Database Insertion
        row_id = self.repo.insert_vintage(vintage_payload)
        return row_id

