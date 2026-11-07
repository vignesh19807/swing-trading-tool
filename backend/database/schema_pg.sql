-- =============================================================================
-- PostgreSQL 16 Canonical Schema
-- Swing Trading Intelligence Platform (Indian Equities)
-- =============================================================================
-- Target Database: PostgreSQL 16 (Neon Serverless PostgreSQL / Cloud Staging)
-- Dialect Differences from SQLite:
-- 1. Primary keys use BIGSERIAL PRIMARY KEY instead of INTEGER PRIMARY KEY AUTOINCREMENT.
-- 2. Foreign key constraints are enforced natively by the relational engine.
-- 3. Booleans are native BOOLEAN instead of INTEGER (0/1).
-- 4. Dates are native DATE ('YYYY-MM-DD') and timestamps are TIMESTAMPTZ.
-- 5. Financial figures and prices use DOUBLE PRECISION.
-- 6. Generated columns use GENERATED ALWAYS AS (...) STORED (PostgreSQL requires STORED).
-- 7. Immutability triggers are defined via PL/pgSQL trigger functions with RAISE EXCEPTION.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Sectors & Industries (Taxonomy)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sectors (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS industries (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sector_id BIGINT NOT NULL REFERENCES sectors(id) ON DELETE RESTRICT,
    UNIQUE(name, sector_id)
);

CREATE INDEX IF NOT EXISTS idx_industries_sector_id ON industries(sector_id);

-- -----------------------------------------------------------------------------
-- 2. Companies (Universe Master & Lifecycle)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS companies (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    exchange VARCHAR(20) NOT NULL DEFAULT 'NSE',
    sector_id BIGINT REFERENCES sectors(id) ON DELETE SET NULL,
    industry_id BIGINT REFERENCES industries(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    listing_date DATE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) DEFAULT 'INITIAL_UNIVERSE'
);

CREATE INDEX IF NOT EXISTS idx_companies_symbol ON companies(symbol);
CREATE INDEX IF NOT EXISTS idx_companies_sector_id ON companies(sector_id);
CREATE INDEX IF NOT EXISTS idx_companies_industry_id ON companies(industry_id);
CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status, is_active);

-- -----------------------------------------------------------------------------
-- 3. Daily OHLCV Prices
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    adjusted_close DOUBLE PRECISION,
    UNIQUE(company_id, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_company_date ON daily_prices(company_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices(date);

-- -----------------------------------------------------------------------------
-- 4. Technical Indicators
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS technical_indicators (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    rsi DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    ema_20 DOUBLE PRECISION,
    ema_50 DOUBLE PRECISION,
    ema_200 DOUBLE PRECISION,
    macd_histogram DOUBLE PRECISION,
    atr_14 DOUBLE PRECISION,
    technical_score DOUBLE PRECISION,
    UNIQUE(company_id, date)
);

CREATE INDEX IF NOT EXISTS idx_technical_indicators_company_date ON technical_indicators(company_id, date);

-- -----------------------------------------------------------------------------
-- 5. Quarterly Results (Legacy Financials)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS quarterly_results (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    quarter VARCHAR(20) NOT NULL,
    revenue DOUBLE PRECISION,
    net_profit DOUBLE PRECISION,
    eps DOUBLE PRECISION,
    roe DOUBLE PRECISION,
    roce DOUBLE PRECISION,
    debt_equity DOUBLE PRECISION,
    operating_margin DOUBLE PRECISION,
    net_margin DOUBLE PRECISION,
    publication_date DATE,
    UNIQUE(company_id, quarter)
);

CREATE INDEX IF NOT EXISTS idx_quarterly_results_company_quarter ON quarterly_results(company_id, quarter);
CREATE INDEX IF NOT EXISTS idx_quarterly_results_quarter ON quarterly_results(quarter);
CREATE INDEX IF NOT EXISTS idx_quarterly_results_pub_date ON quarterly_results(company_id, publication_date);

-- -----------------------------------------------------------------------------
-- 6. Quarterly Financial Vintages (Point-in-Time Research & Governance)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS quarterly_financial_vintages (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    quarter VARCHAR(20) NOT NULL,
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,
    accounting_standard VARCHAR(20) NOT NULL DEFAULT 'IND_AS' CHECK(accounting_standard IN ('IND_AS', 'IGAAP')),
    filing_scope VARCHAR(20) NOT NULL DEFAULT 'CONSOLIDATED' CHECK(filing_scope IN ('CONSOLIDATED', 'STANDALONE')),
    
    -- 1. Four Independent Classification Dimensions (P2.6)
    company_filing_type VARCHAR(50) NOT NULL CHECK(company_filing_type IN (
        'ORIGINAL', 'REVISED_DISCLOSURE', 'CORPORATE_RESTATEMENT', 'ANNUAL_AUDITED_FINAL'
    )),
    internal_revision_type VARCHAR(50) NOT NULL DEFAULT 'INITIAL_INGESTION' CHECK(internal_revision_type IN (
        'INITIAL_INGESTION', 'EXTRACTION_CORRECTION', 'SCOPE_REALIGNMENT', 'SECTOR_NORMALIZATION'
    )),
    verification_status VARCHAR(20) NOT NULL DEFAULT 'PROVISIONAL' CHECK(verification_status IN (
        'VERIFIED', 'PROVISIONAL', 'REJECTED'
    )),
    research_eligibility VARCHAR(30) NOT NULL DEFAULT 'PROVISIONAL_DEMO' CHECK(research_eligibility IN (
        'VERIFIED_ELIGIBLE', 'PROVISIONAL_DEMO', 'QUARANTINED', 'SUPERSEDED'
    )),

    -- 2. Versioning & Lineage Model
    version_sequence INTEGER NOT NULL DEFAULT 1 CHECK(version_sequence >= 1),
    parent_vintage_id BIGINT REFERENCES quarterly_financial_vintages(id),
    supersedes_vintage_id BIGINT REFERENCES quarterly_financial_vintages(id),
    superseded_by_vintage_id BIGINT REFERENCES quarterly_financial_vintages(id),
    revision_reason TEXT,
    revision_source TEXT,
    lineage_created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- 3. Canonical Timestamps
    exchange VARCHAR(10) NOT NULL CHECK(exchange IN ('NSE', 'BSE')),
    exchange_broadcast_id VARCHAR(100) NOT NULL,
    original_broadcast_id VARCHAR(100),
    published_at TIMESTAMPTZ NOT NULL,
    effective_trading_date DATE NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    internally_corrected_at TIMESTAMPTZ,
    company_revision_published_at TIMESTAMPTZ,

    -- 4. Disaggregated Operating Financials (in INR Crores)
    revenue DOUBLE PRECISION NOT NULL,
    revenue_from_operations DOUBLE PRECISION,
    gross_revenue DOUBLE PRECISION,
    total_income DOUBLE PRECISION,
    operating_expenses DOUBLE PRECISION,
    operating_profit DOUBLE PRECISION,
    net_profit DOUBLE PRECISION NOT NULL,
    eps DOUBLE PRECISION NOT NULL,

    -- 5. Sector-Aware Banking / Financial Institutions Metrics
    is_banking_institution BOOLEAN NOT NULL DEFAULT FALSE,
    net_interest_income DOUBLE PRECISION,
    customer_deposits DOUBLE PRECISION,
    capital_adequacy_ratio DOUBLE PRECISION,
    gross_npa_pct DOUBLE PRECISION,
    net_npa_pct DOUBLE PRECISION,

    -- 6. Standard Balance Sheet Line Items
    total_assets DOUBLE PRECISION,
    total_equity DOUBLE PRECISION,
    total_debt DOUBLE PRECISION,
    current_liabilities DOUBLE PRECISION,

    -- 7. Materialized Financial Ratios
    roe DOUBLE PRECISION,
    roce DOUBLE PRECISION,
    debt_equity DOUBLE PRECISION,
    operating_margin DOUBLE PRECISION,
    net_margin DOUBLE PRECISION,

    -- 8. Provenance & Audit Metadata
    source_document_url TEXT NOT NULL,
    source_document_hash VARCHAR(64) NOT NULL,
    verification_notes TEXT,
    remediation_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    remediation_type VARCHAR(50),
    internal_correction_event_id VARCHAR(100),

    -- Virtual aliases generated for backward-compatibility (PostgreSQL requires STORED)
    filing_type VARCHAR(50) GENERATED ALWAYS AS (company_filing_type) STORED,
    publication_timestamp TIMESTAMPTZ GENERATED ALWAYS AS (published_at) STORED,

    -- Integrity Constraints
    CHECK(superseded_by_vintage_id IS NULL OR superseded_by_vintage_id <> id),
    CHECK(supersedes_vintage_id IS NULL OR supersedes_vintage_id <> id),
    CHECK(parent_vintage_id IS NULL OR parent_vintage_id <> id),
    CHECK(NOT is_banking_institution OR debt_equity IS NULL),

    UNIQUE(exchange, exchange_broadcast_id),
    UNIQUE(company_id, quarter, filing_scope, version_sequence)
);

CREATE INDEX IF NOT EXISTS idx_qfv_company_quarter ON quarterly_financial_vintages(company_id, quarter);
CREATE INDEX IF NOT EXISTS idx_qfv_effective_date ON quarterly_financial_vintages(company_id, effective_trading_date);
CREATE INDEX IF NOT EXISTS idx_qfv_eligibility ON quarterly_financial_vintages(company_id, research_eligibility);

-- -----------------------------------------------------------------------------
-- 7. Signals & Scores (Decision Intelligence)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    signal VARCHAR(20),
    entry_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    target_price DOUBLE PRECISION,
    confidence DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_signals_company_date ON signals(company_id, date);

CREATE TABLE IF NOT EXISTS financial_scores (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    profitability_score DOUBLE PRECISION,
    growth_score DOUBLE PRECISION,
    valuation_score DOUBLE PRECISION,
    overall_score DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_financial_scores_company_date ON financial_scores(company_id, date);

CREATE TABLE IF NOT EXISTS opportunity_scores (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    technical_score DOUBLE PRECISION,
    financial_score DOUBLE PRECISION,
    momentum_score DOUBLE PRECISION,
    opportunity_score DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_opportunity_scores_company_date ON opportunity_scores(company_id, date);

-- -----------------------------------------------------------------------------
-- 8. Backtest Framework & Historical Ledger
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id VARCHAR(100) PRIMARY KEY,
    strategy_version VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DOUBLE PRECISION NOT NULL,
    config_json TEXT NOT NULL,
    status VARCHAR(30) NOT NULL,
    metrics_json TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    evaluation_date DATE NOT NULL,
    result_metadata TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_id, symbol, evaluation_date)
);

CREATE INDEX IF NOT EXISTS idx_backtest_results_run_symbol_date ON backtest_results(run_id, symbol, evaluation_date);

CREATE TABLE IF NOT EXISTS backtest_trades (
    id BIGSERIAL PRIMARY KEY,
    trade_id VARCHAR(100) UNIQUE NOT NULL,
    run_id VARCHAR(100) NOT NULL REFERENCES backtest_runs(run_id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    signal_date DATE NOT NULL,
    entry_date DATE NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    exit_date DATE,
    exit_price DOUBLE PRECISION,
    quantity BIGINT NOT NULL,
    initial_value DOUBLE PRECISION NOT NULL,
    gross_pl DOUBLE PRECISION,
    entry_costs DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    exit_costs DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_costs DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    net_pl DOUBLE PRECISION,
    return_pct DOUBLE PRECISION,
    status VARCHAR(30) NOT NULL,
    exit_reason TEXT,
    holding_days INTEGER DEFAULT 0,
    trade_metadata TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backtest_trades_run_symbol ON backtest_trades(run_id, symbol);

CREATE TABLE IF NOT EXISTS backtest_equity_curve (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL REFERENCES backtest_runs(run_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    cash DOUBLE PRECISION NOT NULL,
    positions_value DOUBLE PRECISION NOT NULL,
    total_equity DOUBLE PRECISION NOT NULL,
    drawdown_pct DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_id, date)
);

CREATE INDEX IF NOT EXISTS idx_backtest_equity_curve_run_date ON backtest_equity_curve(run_id, date);

-- -----------------------------------------------------------------------------
-- 9. Universe Audit Log
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS universe_audit_log (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(30) NOT NULL,
    old_values_json TEXT,
    new_values_json TEXT,
    initiated_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    notes TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_universe_audit_log_symbol ON universe_audit_log(symbol);

-- =============================================================================
-- 10. Financial Immutability PL/pgSQL Triggers
-- =============================================================================

-- Trigger 1: Deletion Prevention
CREATE OR REPLACE FUNCTION trg_fn_prevent_vintage_deletion()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Illegal deletion: Historical financial vintages are immutable and cannot be deleted.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_vintage_deletion ON quarterly_financial_vintages;
CREATE TRIGGER trg_prevent_vintage_deletion
BEFORE DELETE ON quarterly_financial_vintages
FOR EACH ROW EXECUTE FUNCTION trg_fn_prevent_vintage_deletion();

-- Trigger 2: Mutation Prevention
CREATE OR REPLACE FUNCTION trg_fn_prevent_vintage_financial_mutation()
RETURNS TRIGGER AS $$
BEGIN
    -- Prohibit mutating reported financial figures, timestamps, or core identity
    IF (NEW.company_id <> OLD.company_id)
       OR (NEW.quarter <> OLD.quarter)
       OR (NEW.version_sequence <> OLD.version_sequence)
       OR (NEW.filing_scope <> OLD.filing_scope)
       OR (NEW.published_at <> OLD.published_at)
       OR (NEW.effective_trading_date <> OLD.effective_trading_date)
       OR (NEW.revenue <> OLD.revenue)
       OR (NEW.net_profit <> OLD.net_profit)
       OR (NEW.eps <> OLD.eps) THEN
        RAISE EXCEPTION 'Illegal mutation: Financial figures and publication timestamps are immutable. Insert a new vintage instead.';
    END IF;

    -- Prohibit self-supersession
    IF (NEW.superseded_by_vintage_id IS NOT NULL AND NEW.superseded_by_vintage_id = OLD.id)
       OR (NEW.supersedes_vintage_id IS NOT NULL AND NEW.supersedes_vintage_id = OLD.id)
       OR (NEW.parent_vintage_id IS NOT NULL AND NEW.parent_vintage_id = OLD.id) THEN
        RAISE EXCEPTION 'Illegal lineage: A vintage cannot reference or supersede itself.';
    END IF;

    -- Prohibit circular lineage
    IF (NEW.superseded_by_vintage_id IS NOT NULL AND NEW.superseded_by_vintage_id = OLD.supersedes_vintage_id) THEN
        RAISE EXCEPTION 'Illegal circular lineage: A vintage cannot be superseded by the vintage it supersedes.';
    END IF;

    -- Prohibit promoting to VERIFIED_ELIGIBLE without verification_status = VERIFIED
    IF (NEW.research_eligibility = 'VERIFIED_ELIGIBLE' AND NEW.verification_status <> 'VERIFIED') THEN
        RAISE EXCEPTION 'Illegal promotion: Record cannot be VERIFIED_ELIGIBLE without verification_status = VERIFIED.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_vintage_financial_mutation ON quarterly_financial_vintages;
CREATE TRIGGER trg_prevent_vintage_financial_mutation
BEFORE UPDATE ON quarterly_financial_vintages
FOR EACH ROW EXECUTE FUNCTION trg_fn_prevent_vintage_financial_mutation();

-- Trigger 3: Insertion Integrity & Conflation Prevention
CREATE OR REPLACE FUNCTION trg_fn_prevent_extraction_restatement_conflation()
RETURNS TRIGGER AS $$
BEGIN
    -- Prohibit semantic conflation of internal fixes with corporate restatements
    IF NEW.internal_revision_type IN ('EXTRACTION_CORRECTION', 'SCOPE_REALIGNMENT', 'SECTOR_NORMALIZATION')
       AND NEW.company_filing_type = 'CORPORATE_RESTATEMENT' THEN
        RAISE EXCEPTION 'Semantic Conflation Error: Internal pipeline revisions cannot populate company_filing_type as CORPORATE_RESTATEMENT.';
    END IF;

    -- Prohibit inserting as VERIFIED_ELIGIBLE without verification_status = VERIFIED
    IF NEW.research_eligibility = 'VERIFIED_ELIGIBLE' AND NEW.verification_status <> 'VERIFIED' THEN
        RAISE EXCEPTION 'Integrity Error: Cannot insert VERIFIED_ELIGIBLE vintage without verification_status = VERIFIED.';
    END IF;

    -- Prohibit self-supersession
    IF NEW.superseded_by_vintage_id IS NOT NULL AND NEW.superseded_by_vintage_id = NEW.id THEN
        RAISE EXCEPTION 'Lineage Error: A vintage cannot supersede itself.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_extraction_restatement_conflation ON quarterly_financial_vintages;
CREATE TRIGGER trg_prevent_extraction_restatement_conflation
BEFORE INSERT ON quarterly_financial_vintages
FOR EACH ROW EXECUTE FUNCTION trg_fn_prevent_extraction_restatement_conflation();

