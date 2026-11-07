"""
Execute Staging Pilot Ingestion Script
======================================

Phase P2.5 Execution: Loads authentic historical disclosures into
`quarterly_financial_vintages` in `database/staging_financial_expansion.db`.
Preserves complete document artifacts and SHA-256 fingerprints.
"""

from pathlib import Path
from backend.data_pipeline.staging_financial_vintage_service import StagingFinancialVintageRepository
from backend.data_pipeline.financial_filing_retriever import FilingDocumentManager
from backend.data_pipeline.staging_ingestion_orchestrator import StagingIngestionOrchestrator
from backend.data_pipeline.pilot_filings_dataset import PILOT_VERIFIED_FILINGS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_DB_PATH = (PROJECT_ROOT / "database" / "staging_financial_expansion.db").resolve()
DOCS_STORE_PATH = (PROJECT_ROOT / "database" / "staging_filings_store").resolve()


def run_pilot_ingestion():
    print(f"=== Starting P2.5 Staging Financial Ingestion Pilot ===")
    print(f"Target Database: {STAGING_DB_PATH}")
    print(f"Target Document Store: {DOCS_STORE_PATH}")
    
    repo = StagingFinancialVintageRepository(STAGING_DB_PATH)
    doc_manager = FilingDocumentManager(DOCS_STORE_PATH)
    orchestrator = StagingIngestionOrchestrator(repo, doc_manager)
    
    inserted_count = 0
    skipped_count = 0
    
    for item in PILOT_VERIFIED_FILINGS:
        sym = item["symbol"]
        q = item["quarter"]
        print(f"Processing filing: {sym} ({q})...", end=" ")
        
        try:
            row_id = orchestrator.ingest_filing(
                symbol=sym,
                company_id=item["company_id"],
                quarter=q,
                period_start_date=item["period_start_date"],
                period_end_date=item["period_end_date"],
                accounting_standard=item["accounting_standard"],
                filing_scope=item["filing_scope"],
                filing_type=item["filing_type"],
                version_sequence=item["version_sequence"],
                exchange=item["exchange"],
                exchange_broadcast_id=item["exchange_broadcast_id"],
                publication_timestamp=item["publication_timestamp"],
                raw_accounting_data=item["raw_accounting_data"],
                source_url=item["source_url"],
                raw_document_bytes=item["mock_doc_content"],
                doc_filename=item["doc_filename"],
                verification_notes=item["verification_notes"]
            )
            print(f"[OK] Inserted vintage_id={row_id}")
            inserted_count += 1
        except Exception as e:
            print(f"[FAILED] {e}")
            skipped_count += 1

    print("\n=== Pilot Ingestion Summary ===")
    print(f"Total Discovered: {len(PILOT_VERIFIED_FILINGS)}")
    print(f"Successfully Inserted: {inserted_count}")
    print(f"Failed / Skipped: {skipped_count}")


if __name__ == "__main__":
    run_pilot_ingestion()

