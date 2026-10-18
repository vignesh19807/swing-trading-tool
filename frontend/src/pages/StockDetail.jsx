import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Sparkles,
  ShieldAlert,
  BarChart2,
  CheckCircle2,
  Building2,
} from 'lucide-react';
import { getStock, getStockHistory } from '../services/api';
import { normalizeStockData } from '../utils/tradingSetup';
import { formatCurrency, formatPercent, formatScore } from '../utils/formatters';
import { computeAllIndicators } from '../utils/technicalIndicators';
import TradingSetupCard, { DirectionBadge } from '../components/TradingSetupCard';
import TechnicalAnalysisCard from '../components/TechnicalAnalysisCard';
import { PriceChart } from '../charts';
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents';
import WatchlistButton from '../components/WatchlistButton';

const ScoreBar = ({ label, score, weight = null }) => {
  if (score == null || isNaN(score)) {
    return (
      <div className="flex justify-between items-center py-2 text-xs border-b border-border-primary/60 last:border-0">
        <span className="text-tx-secondary">{label}</span>
        <span className="text-tx-muted font-mono">—</span>
      </div>
    );
  }

  const num = Number(score);
  const percentage = Math.min(Math.max(num, 0), 100);
  let color = 'bg-accent-green';
  if (percentage < 50) color = 'bg-accent-red';
  else if (percentage < 70) color = 'bg-accent-warning';

  return (
    <div className="py-2.5 border-b border-border-primary/60 last:border-0">
      <div className="flex justify-between items-center text-xs mb-1.5">
        <span className="font-medium text-tx-secondary flex items-center gap-1.5">
          {label}
          {weight && <span className="text-[10px] text-tx-muted">({weight})</span>}
        </span>
        <span className="font-mono font-bold text-tx-primary">{num.toFixed(1)}</span>
      </div>
      <div className="h-2 w-full bg-surface-secondary rounded-full overflow-hidden">
        <div className={`h-full ${color} transition-all duration-300`} style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
};

const StockDetail = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();

  const safeSymbol = symbol
    ? decodeURIComponent(symbol).toUpperCase().replace(/[^A-Z0-9-]/g, '')
    : '';

  const [state, setState] = useState(() => ({
    data: null,
    loading: Boolean(safeSymbol),
    error: safeSymbol ? null : 'Invalid stock symbol provided.',
  }));

  const [historyState, setHistoryState] = useState(() => ({
    data: [],
    loading: Boolean(safeSymbol),
    error: null,
  }));

  // Synchronized Technical Indicator Controls (Phase 15)
  const [activeIndicators, setActiveIndicators] = useState({
    ema20: true,
    ema50: true,
    ema200: false,
    rsi: true,
    macd: true,
  });

  const handleToggleIndicator = useCallback((key) => {
    setActiveIndicators((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  // Compute all technical indicators from history
  const indicators = useMemo(() => {
    return computeAllIndicators(historyState.data);
  }, [historyState.data]);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchStock = useCallback(async () => {
    if (!safeSymbol) return;
    setIsRefreshing(true);

    try {
      const [resStock, resHistory] = await Promise.allSettled([
        getStock(safeSymbol),
        getStockHistory(safeSymbol),
      ]);

      if (resStock.status === 'fulfilled' && resStock.value) {
        setState({ data: normalizeStockData(resStock.value), loading: false, error: null });
      } else if (resStock.status === 'rejected') {
        setState({
          data: null,
          loading: false,
          error: resStock.reason?.message || 'Failed to retrieve stock intelligence.',
        });
      } else {
        setState({ data: null, loading: false, error: `No intelligence data available for ${safeSymbol}.` });
      }

      if (resHistory.status === 'fulfilled' && Array.isArray(resHistory.value)) {
        setHistoryState({ data: resHistory.value, loading: false, error: null });
      } else if (resHistory.status === 'rejected') {
        setHistoryState({
          data: [],
          loading: false,
          error: resHistory.reason?.message || 'Failed to load historical price data.',
        });
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [safeSymbol]);

  useEffect(() => {
    if (!safeSymbol) return;

    let isMounted = true;

    Promise.allSettled([
      getStock(safeSymbol),
      getStockHistory(safeSymbol),
    ]).then(([resStock, resHistory]) => {
      if (!isMounted) return;

      if (resStock.status === 'fulfilled' && resStock.value) {
        setState({ data: normalizeStockData(resStock.value), loading: false, error: null });
      } else if (resStock.status === 'rejected') {
        setState({
          data: null,
          loading: false,
          error: resStock.reason?.message || 'Failed to retrieve stock intelligence.',
        });
      } else {
        setState({ data: null, loading: false, error: `No intelligence data available for ${safeSymbol}.` });
      }

      if (resHistory.status === 'fulfilled' && Array.isArray(resHistory.value)) {
        setHistoryState({ data: resHistory.value, loading: false, error: null });
      } else if (resHistory.status === 'rejected') {
        setHistoryState({
          data: [],
          loading: false,
          error: resHistory.reason?.message || 'Failed to load historical price data.',
        });
      }
    });

    return () => {
      isMounted = false;
    };
  }, [safeSymbol]);

  // Loading State
  if (state.loading) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
        <div className="flex items-center gap-2 text-xs text-tx-muted mb-4">
          <Link to="/opportunities" className="hover:text-tx-primary">Opportunities</Link>
          <span>/</span>
          <span>Stocks</span>
          <span>/</span>
          <span className="text-tx-primary">{safeSymbol || 'Detail'}</span>
        </div>
        <LoadingState message={`Analyzing swing trading intelligence for ${safeSymbol}...`} className="min-h-[400px]" />
      </div>
    );
  }

  // Error State
  if (state.error) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
        <div className="flex items-center gap-2 text-xs text-tx-muted mb-4">
          <Link to="/opportunities" className="hover:text-tx-primary">Opportunities</Link>
          <span>/</span>
          <span className="text-tx-primary">{safeSymbol || 'Error'}</span>
        </div>
        <ErrorState
          title={`Error loading ${safeSymbol || 'stock'}`}
          message={state.error}
          onRetry={() => {
            setState((prev) => ({ ...prev, loading: true, error: null }));
            setHistoryState((prev) => ({ ...prev, loading: true, error: null }));
            fetchStock();
          }}
          className="min-h-[300px]"
        />
        <div className="text-center pt-2">
          <Link
            to="/opportunities"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent-green hover:underline"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Opportunities Explorer
          </Link>
        </div>
      </div>
    );
  }

  const stock = state.data;
  if (!stock) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
        <EmptyState
          message={`Stock "${safeSymbol}" could not be located in the current universe.`}
          className="min-h-[300px]"
        />
        <div className="text-center pt-2">
          <Link
            to="/opportunities"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent-green hover:underline"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Return to Opportunities Explorer
          </Link>
        </div>
      </div>
    );
  }

  const isPositiveChange = stock.priceChangePercent != null ? stock.priceChangePercent >= 0 : null;

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-8 animate-fade-in">
      {/* Breadcrumb & Navigation Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs text-tx-muted flex-wrap">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1 text-tx-secondary hover:text-tx-primary font-medium transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back
          </button>
          <span>•</span>
          <Link to="/opportunities" className="hover:text-tx-primary transition-colors">Opportunities</Link>
          <span>/</span>
          <Link to="/stocks" className="hover:text-tx-primary transition-colors">Stocks</Link>
          <span>/</span>
          <span className="font-semibold text-tx-primary font-mono">{stock.symbol}</span>
        </div>

        <div className="flex items-center gap-2.5 self-end sm:self-auto flex-wrap">
          <WatchlistButton stock={stock} variant="button" size="md" />
          <button
            type="button"
            onClick={fetchStock}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-border-primary bg-surface text-tx-secondary hover:text-tx-primary hover:bg-surface-secondary text-xs sm:text-sm font-semibold transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
            title="Refresh Stock Intelligence"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-accent-green' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Data'}</span>
          </button>
        </div>
      </div>

      {/* Stock Header Banner */}
      <div className="bg-surface rounded-2xl border border-border-primary p-6 sm:p-7 shadow-sm transition-colors">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          {/* Identity & Classification */}
          <div>
            <div className="flex items-center gap-3 flex-wrap mb-2">
              <h1 className="font-heading font-bold text-3xl sm:text-4xl text-tx-primary tracking-tight">
                {stock.symbol}
              </h1>
              <WatchlistButton stock={stock} size="lg" />
              <DirectionBadge recommendation={stock.recommendation} />
              {stock.sector && stock.sector !== '—' && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-medium rounded-md bg-surface-secondary text-tx-secondary border border-border-primary">
                  <Building2 className="w-3 h-3" />
                  {stock.sector}
                </span>
              )}
            </div>
            <p className="text-sm sm:text-base text-tx-secondary font-medium">
              {stock.companyName}
              {stock.industry && stock.industry !== '—' && (
                <span className="text-tx-muted font-normal"> • {stock.industry}</span>
              )}
            </p>
          </div>

          {/* Current Market Price & Daily Performance */}
          <div className="flex items-baseline lg:items-end flex-col border-t lg:border-t-0 pt-4 lg:pt-0 border-border-primary">
            <div className="text-[11px] font-semibold tracking-wider uppercase text-tx-muted mb-0.5">
              Current Market Price
            </div>
            <div className="flex items-baseline gap-3">
              <span className="font-heading font-bold text-3xl sm:text-4xl text-tx-primary font-mono tracking-tight">
                {formatCurrency(stock.currentPrice)}
              </span>
              {stock.priceChangePercent != null && (
                <span
                  className={`inline-flex items-center gap-0.5 text-sm font-bold font-mono px-2 py-0.5 rounded-md ${
                    isPositiveChange
                      ? 'bg-accent-green/10 text-accent-green'
                      : 'bg-accent-red/10 text-accent-red'
                  }`}
                >
                  {isPositiveChange ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  {formatPercent(stock.priceChangePercent)}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* PHASE 14: Interactive Historical Stock Price Chart */}
      <section aria-label="Interactive Historical Stock Price Chart">
        <PriceChart
          symbol={stock.symbol}
          data={historyState.data}
          loading={historyState.loading}
          error={historyState.error}
          onRetry={fetchStock}
          setupLevels={{
            entry: stock.entryPrice,
            stopLoss: stock.stopLoss,
            target: stock.target,
          }}
          indicatorsConfig={activeIndicators}
          onToggleIndicator={handleToggleIndicator}
        />
      </section>

      {/* PHASE 15: Technical Analysis Interface */}
      <section aria-label="Technical Analysis Interface">
        <TechnicalAnalysisCard
          stock={stock}
          indicators={indicators}
          activeIndicators={activeIndicators}
          onToggleIndicator={handleToggleIndicator}
        />
      </section>

      {/* PHASE 13: Trading Setup & Risk/Reward Interface */}
      <section aria-label="Trading Setup and Risk/Reward">
        <TradingSetupCard stock={stock} />
      </section>

      {/* Secondary Section: Multi-Factor Intelligence & Catalysts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Multi-Factor Scores Card */}
        <div className="bg-surface rounded-2xl border border-border-primary p-5 sm:p-6 shadow-sm transition-colors lg:col-span-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 mb-2 border-b border-border-primary">
              <div className="flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-accent-teal" />
                <h3 className="font-heading font-semibold text-base text-tx-primary">
                  Multi-Factor Scores
                </h3>
              </div>
              <span className="text-xs font-bold font-mono text-accent-green bg-accent-green/10 px-2 py-0.5 rounded">
                Score: {formatScore(stock.opportunityScore)}
              </span>
            </div>

            <p className="text-xs text-tx-secondary mb-4 leading-relaxed">
              Algorithmic scoring composite evaluated from technical momentum, financial quality, and volatility.
            </p>

            <div className="space-y-1">
              <ScoreBar label="Opportunity Score" score={stock.opportunityScore} />
              <ScoreBar label="Technical Score" score={stock.technicalScore} weight="40%" />
              <ScoreBar label="Financial Score" score={stock.financialScore} weight="35%" />
              <ScoreBar label="Momentum Score" score={stock.momentumScore} weight="25%" />
              <ScoreBar label="Risk Assessment" score={stock.riskScore != null ? 100 - stock.riskScore : null} />
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-border-primary text-[11px] text-tx-muted">
            All sub-scores are calculated over 21-day to 252-day time horizons.
          </div>
        </div>

        {/* Qualitative Catalysts & Risk Factors */}
        <div className="bg-surface rounded-2xl border border-border-primary p-5 sm:p-6 shadow-sm transition-colors lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-center gap-2 pb-4 mb-4 border-b border-border-primary">
              <Sparkles className="w-4 h-4 text-accent-teal" />
              <h3 className="font-heading font-semibold text-base text-tx-primary">
                Setup Rationale & Intelligence
              </h3>
            </div>

            {stock.explanation && (
              <div className="p-4 rounded-xl bg-surface-secondary/60 border border-border-primary/80 mb-6 text-xs sm:text-sm text-tx-primary leading-relaxed font-sans">
                {stock.explanation}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Bullish Factors */}
              <div className="p-4 rounded-xl bg-accent-green/5 border border-accent-green/20">
                <div className="flex items-center gap-2 text-xs font-bold text-accent-green uppercase tracking-wider mb-3">
                  <CheckCircle2 className="w-4 h-4" />
                  Supporting Factors
                </div>
                {stock.bullishFactors && stock.bullishFactors.length > 0 ? (
                  <ul className="space-y-2">
                    {stock.bullishFactors.map((factor, idx) => (
                      <li key={idx} className="text-xs text-tx-secondary flex items-start gap-2 leading-relaxed">
                        <span className="text-accent-green mt-0.5">•</span>
                        <span>{factor}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-tx-muted italic">No specific positive catalysts detected.</p>
                )}
              </div>

              {/* Risk Factors */}
              <div className="p-4 rounded-xl bg-accent-red/5 border border-accent-red/20">
                <div className="flex items-center gap-2 text-xs font-bold text-accent-red uppercase tracking-wider mb-3">
                  <ShieldAlert className="w-4 h-4" />
                  Risk Considerations
                </div>
                {stock.riskFactors && stock.riskFactors.length > 0 ? (
                  <ul className="space-y-2">
                    {stock.riskFactors.map((risk, idx) => (
                      <li key={idx} className="text-xs text-tx-secondary flex items-start gap-2 leading-relaxed">
                        <span className="text-accent-red mt-0.5">•</span>
                        <span>{risk}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-tx-muted italic">No elevated risk flags noted.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StockDetail;
