/**
 * @file StockExplorer.jsx
 * @description Phase 16 Stock Explorer & Technical Screener for Indian equities universe.
 * 
 * FEATURES:
 *   - Comprehensive search by symbol, company name, sector, or industry
 *   - Sector, direction (bullish/bearish/neutral), price performance, and signal filters
 *   - Technical strategy filters (EMA 20/50/200, RSI 14 ranges, MACD crossover, MACD Histogram)
 *   - Strictly non-fabricated: stocks with insufficient history are clearly labeled and safely excluded from indicator filters
 *   - Slide-over filter drawer with strategy presets and active filter count
 *   - Removable active filter chips and 1-click Reset All
 *   - In-memory cached technical snapshot calculation to avoid recomputation on render
 *   - Table and responsive Card view modes
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  ArrowUpDown,
  ArrowUpRight,
  TrendingUp,
  TrendingDown,
  Eye,
  RefreshCw,
  X,
  LayoutGrid,
  List,
  SlidersHorizontal,
  Building2,
  Activity,
  AlertCircle
} from 'lucide-react';
import { getStocks, getStockHistory } from '../services/api';
import MetricCard from '../components/MetricCard';
import WatchlistButton from '../components/WatchlistButton';
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents';
import ScreenerFilterDrawer from '../components/ScreenerFilterDrawer';
import {
  DEFAULT_SCREENER_FILTERS,
  getTechnicalSnapshot,
  filterStocks,
  sortStocks,
  countActiveFilters,
  getActiveFilterChips,
} from '../utils/screenerFilters';

const IS_MOCK_MODE = import.meta.env.VITE_USE_MOCK_DATA === 'true';

const ScoreBadge = ({ score, max = 100 }) => {
  if (score == null || isNaN(score)) {
    return <span className="text-xs text-tx-secondary">—</span>;
  }
  const numericScore = Number(score);
  const percentage = Math.min(Math.max((numericScore / max) * 100, 0), 100);
  let color = 'bg-accent-green';
  if (percentage < 50) color = 'bg-accent-red';
  else if (percentage < 70) color = 'bg-accent-warning';

  return (
    <div className="flex items-center gap-2">
      <div className="w-14 h-2 bg-surface-secondary rounded-full overflow-hidden shrink-0">
        <div className={`h-full ${color} transition-all duration-300`} style={{ width: `${percentage}%` }} />
      </div>
      <span className="text-xs font-semibold text-tx-primary font-mono">{numericScore.toFixed(1)}</span>
    </div>
  );
};

const RecommendationBadge = ({ recommendation }) => {
  if (!recommendation) {
    return <span className="text-xs text-tx-secondary">—</span>;
  }
  const rec = recommendation.toUpperCase();
  if (rec === 'BUY' || rec === 'BULLISH') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded-md bg-accent-green/10 text-accent-green border border-accent-green/20">
        <TrendingUp className="w-3 h-3 shrink-0" />
        Buy
      </span>
    );
  }
  if (rec === 'SELL' || rec === 'BEARISH') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded-md bg-accent-red/10 text-accent-red border border-accent-red/20">
        <TrendingDown className="w-3 h-3 shrink-0" />
        Sell
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded-md bg-surface-secondary text-tx-secondary border border-border-primary">
      <Eye className="w-3 h-3 shrink-0" />
      Watch
    </span>
  );
};

const TechnicalIndicatorCell = ({ technicals, compact = false }) => {
  if (!technicals) {
    return (
      <span className="text-xs text-tx-muted font-mono inline-flex items-center gap-1">
        <RefreshCw className="w-3 h-3 animate-spin text-tx-muted" />
        <span>Calculating...</span>
      </span>
    );
  }

  if (technicals.isInsufficient || technicals.rsi == null) {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-accent-warning/10 text-accent-warning border border-accent-warning/20"
        title={`Only ${technicals.historyLength || 0} bars available. Insufficient historical data for technical indicators.`}
      >
        <AlertCircle className="w-3 h-3 shrink-0" />
        <span>Insufficient History</span>
      </span>
    );
  }

  const { rsi, close, ema20, ema50, macd, signal } = technicals;

  // RSI status badge styling
  let rsiClass = 'bg-surface-secondary text-tx-primary border-border-primary';
  let rsiLabel = 'Neutral';
  if (rsi >= 70) {
    rsiClass = 'bg-accent-teal/10 text-accent-teal border-accent-teal/30';
    rsiLabel = 'Overbought';
  } else if (rsi <= 30) {
    rsiClass = 'bg-accent-red/10 text-accent-red border-accent-red/30';
    rsiLabel = 'Oversold';
  } else if (rsi >= 50) {
    rsiClass = 'bg-accent-green/10 text-accent-green border-accent-green/30';
    rsiLabel = 'Bullish';
  }

  // EMA trend alignment
  let emaLabel = '—';
  let emaClass = 'text-tx-secondary';
  if (close != null && ema20 != null && ema50 != null) {
    if (close > ema20 && close > ema50) {
      emaLabel = '> EMA 20/50';
      emaClass = 'text-accent-green font-semibold';
    } else if (close < ema20 && close < ema50) {
      emaLabel = '< EMA 20/50';
      emaClass = 'text-accent-red font-semibold';
    } else {
      emaLabel = 'Mixed EMAs';
      emaClass = 'text-tx-secondary';
    }
  }

  // MACD alignment
  const macdCross = (macd != null && signal != null) ? (macd >= signal ? 'Bullish' : 'Bearish') : null;

  if (compact) {
    return (
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${rsiClass}`}
          title={`RSI 14: ${rsi.toFixed(1)} (${rsiLabel})`}
        >
          RSI {rsi.toFixed(0)}
        </span>
        <span className={`text-[11px] font-mono ${emaClass}`}>
          {emaLabel}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${rsiClass}`}
          title={`RSI 14: ${rsi.toFixed(1)} (${rsiLabel})`}
        >
          RSI {rsi.toFixed(0)}
        </span>
        <span className={`text-xs font-mono ${emaClass}`} title="Price position relative to EMA 20 & EMA 50">
          {emaLabel}
        </span>
      </div>
      {macdCross && (
        <div className="text-[10px] text-tx-muted font-mono flex items-center gap-1">
          <span>MACD:</span>
          <span className={macdCross === 'Bullish' ? 'text-accent-green' : 'text-accent-red'}>
            {macdCross}
          </span>
        </div>
      )}
    </div>
  );
};

const StockExplorer = () => {
  const [stocksState, setStocksState] = useState({ data: [], loading: true, error: null });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(() => new Date());

  // Technical Snapshots in-memory cache { [symbol]: technicalSnapshot }
  const [technicalsMap, setTechnicalsMap] = useState({});
  const [, setLoadingTechnicals] = useState(false);

  // Screener Filters state
  const [filters, setFilters] = useState(DEFAULT_SCREENER_FILTERS);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [sortBy, setSortBy] = useState('symbol-asc');
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'cards'

  const isMountedRef = useRef(true);

  // Fetch base stocks universe
  const fetchStockList = useCallback(async (isInitial = false) => {
    if (!isInitial) {
      setStocksState(prev => ({ ...prev, loading: true, error: null }));
    }
    try {
      const res = await getStocks();
      if (isMountedRef.current) {
        const list = Array.isArray(res) ? res : res?.stocks || [];
        setStocksState({ data: list, loading: false, error: null });
        setLastRefreshed(new Date());
      }
    } catch (err) {
      if (isMountedRef.current) {
        setStocksState({
          data: [],
          loading: false,
          error: err.message || 'Unable to retrieve stocks from the market intelligence service.'
        });
      }
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await fetchStockList(false);
    } finally {
      if (isMountedRef.current) {
        setIsRefreshing(false);
      }
    }
  }, [fetchStockList]);

  useEffect(() => {
    isMountedRef.current = true;
    const init = async () => {
      await fetchStockList(true);
    };
    init();
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchStockList]);

  const rawStocks = stocksState.data;

  // Asynchronously compute and cache technical snapshots for loaded stocks
  useEffect(() => {
    if (!rawStocks || rawStocks.length === 0) return;

    let active = true;

    const loadTechnicals = async () => {
      setLoadingTechnicals(true);
      const pendingSymbols = rawStocks
        .map(s => s.symbol)
        .filter(sym => sym && !technicalsMap[sym]);

      if (pendingSymbols.length === 0) {
        setLoadingTechnicals(false);
        return;
      }

      const updates = {};
      await Promise.all(
        pendingSymbols.map(async (symbol) => {
          try {
            const history = await getStockHistory(symbol);
            if (active) {
              updates[symbol] = getTechnicalSnapshot(history);
            }
          } catch {
            if (active) {
              updates[symbol] = getTechnicalSnapshot([]); // safe fallback
            }
          }
        })
      );

      if (active && Object.keys(updates).length > 0) {
        setTechnicalsMap(prev => ({ ...prev, ...updates }));
      }
      if (active) {
        setLoadingTechnicals(false);
      }
    };

    loadTechnicals();

    return () => {
      active = false;
    };
  }, [rawStocks, technicalsMap]);

  // Extract distinct sectors dynamically
  const uniqueSectors = useMemo(() => {
    if (!rawStocks) return [];
    const set = new Set();
    rawStocks.forEach(s => {
      if (s.sector) set.add(s.sector);
    });
    return Array.from(set).sort();
  }, [rawStocks]);


  // Check if price changes exist in the dataset
  const hasPriceChanges = useMemo(() => {
    return rawStocks.some(s => s.change_percent != null || s.price_change_percent != null);
  }, [rawStocks]);

  // Apply Screener Filters and Sorting using pure utilities
  const filteredAndSortedStocks = useMemo(() => {
    if (!rawStocks) return [];
    const filtered = filterStocks(rawStocks, filters, technicalsMap);
    return sortStocks(filtered, sortBy, technicalsMap);
  }, [rawStocks, filters, technicalsMap, sortBy]);

  // Summary Metrics calculations
  const summaryMetrics = useMemo(() => {
    if (!rawStocks || rawStocks.length === 0) {
      return { total: 0, buyRated: 0, gainers: 0, decliners: 0 };
    }

    let buyRated = 0;
    let gainers = 0;
    let decliners = 0;

    rawStocks.forEach(s => {
      const rec = (s.recommendation || '').toUpperCase();
      if (rec === 'BUY' || rec === 'BULLISH') buyRated++;

      const changeVal = s.change_percent ?? s.price_change_percent;
      if (changeVal != null && !isNaN(changeVal)) {
        if (Number(changeVal) >= 0) gainers++;
        else decliners++;
      }
    });

    return {
      total: rawStocks.length,
      buyRated,
      gainers,
      decliners
    };
  }, [rawStocks]);

  const activeFiltersCount = countActiveFilters(filters);

  // Active filter chip generation with remove callbacks
  const activeChips = useMemo(() => {
    return getActiveFilterChips(filters, (field, value) => {
      setFilters(prev => ({ ...prev, [field]: value }));
    });
  }, [filters]);

  const resetAllFilters = () => {
    setFilters(DEFAULT_SCREENER_FILTERS);
    setSortBy('symbol-asc');
  };

  const formatCurrency = (val) => {
    if (val == null || isNaN(val)) return '—';
    return `₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* 1. PAGE HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border-primary/50">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-heading font-bold text-tx-primary tracking-tight">
              Stock Screener
            </h1>
            {IS_MOCK_MODE ? (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-accent-teal/10 text-accent-teal border border-accent-teal/20">
                Mock Data Mode
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-accent-green/10 text-accent-green border border-accent-green/20">
                Live API Mode
              </span>
            )}
            {!stocksState.loading && (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-surface-secondary text-tx-secondary border border-border-primary font-mono">
                {filteredAndSortedStocks.length} of {rawStocks.length} Stocks
              </span>
            )}
          </div>
          <p className="text-tx-secondary text-xs sm:text-sm mt-1">
            Technical stock screener & strategy filters across the Indian equities universe.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right hidden sm:block">
            <div className="text-[11px] text-tx-secondary">Last updated</div>
            <div className="text-xs font-mono font-medium text-tx-primary">
              {lastRefreshed ? lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
            </div>
          </div>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing || stocksState.loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface border border-border-primary hover:bg-surface-secondary text-tx-primary text-xs sm:text-sm font-medium transition-colors shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green disabled:opacity-50 cursor-pointer"
            title="Refresh stock universe data"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-accent-green ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* 2. SUMMARY METRICS */}
      <section aria-labelledby="stocks-summary-heading">
        <h2 id="stocks-summary-heading" className="sr-only">Stock Universe Summary</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <MetricCard
            title="Universe Size"
            value={stocksState.loading ? '—' : summaryMetrics.total.toString()}
            subtitle="Covered equities"
            loading={stocksState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-teal/10 text-accent-teal flex items-center justify-center">
                <Building2 className="w-5 h-5" />
              </div>
            }
          />
          <MetricCard
            title="Buy / Bullish"
            value={stocksState.loading ? '—' : summaryMetrics.buyRated.toString()}
            subtitle={summaryMetrics.total > 0 ? `${((summaryMetrics.buyRated / summaryMetrics.total) * 100).toFixed(0)}% of universe` : '0%'}
            isPositive={true}
            loading={stocksState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                <TrendingUp className="w-5 h-5" />
              </div>
            }
          />
          <MetricCard
            title="Daily Gainers"
            value={stocksState.loading ? '—' : summaryMetrics.gainers.toString()}
            subtitle="Positive price change"
            isPositive={true}
            loading={stocksState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                <Activity className="w-5 h-5" />
              </div>
            }
          />
          <MetricCard
            title="Daily Decliners"
            value={stocksState.loading ? '—' : summaryMetrics.decliners.toString()}
            subtitle="Negative price change"
            isPositive={summaryMetrics.decliners === 0 ? null : false}
            loading={stocksState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-red/10 text-accent-red flex items-center justify-center">
                <TrendingDown className="w-5 h-5" />
              </div>
            }
          />
        </div>
      </section>

      {/* 3. SEARCH AND FILTERS BAR */}
      <section className="bg-surface rounded-2xl border border-border-primary shadow-sm p-4 sm:p-5 transition-colors space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          
          {/* Search Input */}
          <div className="relative flex-1 max-w-lg">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-tx-muted" />
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              placeholder="Search by symbol, company name, or sector..."
              className="w-full pl-9 pr-9 py-2 bg-surface-secondary border border-border-primary rounded-xl text-tx-primary text-xs sm:text-sm placeholder:text-tx-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green transition-all"
            />
            {filters.search && (
              <button
                type="button"
                onClick={() => setFilters(prev => ({ ...prev, search: '' }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-tx-muted hover:text-tx-primary p-0.5 rounded cursor-pointer"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Quick Filter Controls Row */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs sm:text-sm">
            {/* Sector Filter */}
            <div className="flex items-center gap-1.5 bg-surface-secondary border border-border-primary rounded-xl px-2.5 py-1.5">
              <label htmlFor="sector-filter" className="sr-only">Filter by Sector</label>
              <select
                id="sector-filter"
                value={filters.sector}
                onChange={(e) => setFilters(prev => ({ ...prev, sector: e.target.value }))}
                className="bg-transparent text-tx-primary text-xs font-medium focus:outline-none cursor-pointer max-w-[140px] sm:max-w-none truncate"
              >
                <option value="ALL">All Sectors</option>
                {uniqueSectors.map(sec => (
                  <option key={sec} value={sec}>{sec}</option>
                ))}
              </select>
            </div>

            {/* Screener & Strategy Filters Trigger Button */}
            <button
              type="button"
              onClick={() => setIsDrawerOpen(true)}
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                activeFiltersCount > 0
                  ? 'bg-accent-green text-surface border-accent-green shadow-xs'
                  : 'bg-surface-secondary border-border-primary text-tx-primary hover:bg-surface-secondary/80'
              }`}
              title="Open Technical Screener & Strategy Filters"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Technical Filters</span>
              {activeFiltersCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-surface text-tx-primary font-mono font-bold">
                  {activeFiltersCount}
                </span>
              )}
            </button>

            {/* Sort By Dropdown */}
            <div className="flex items-center gap-1.5 bg-surface-secondary border border-border-primary rounded-xl px-2.5 py-1.5">
              <ArrowUpDown className="w-3.5 h-3.5 text-tx-muted shrink-0" />
              <label htmlFor="sort-stocks" className="sr-only">Sort stocks</label>
              <select
                id="sort-stocks"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-transparent text-tx-primary text-xs font-medium focus:outline-none cursor-pointer"
              >
                <option value="symbol-asc">Symbol: A to Z</option>
                <option value="symbol-desc">Symbol: Z to A</option>
                <option value="price-desc">Price: High to Low</option>
                <option value="price-asc">Price: Low to High</option>
                {hasPriceChanges && (
                  <>
                    <option value="change-desc">Change: Highest (+)</option>
                    <option value="change-asc">Change: Lowest (-)</option>
                  </>
                )}
                <option value="score-desc">Score: High to Low</option>
                <option value="score-asc">Score: Low to High</option>
                <option value="rsi-desc">RSI: High to Low</option>
                <option value="rsi-asc">RSI: Low to High</option>
              </select>
            </div>

            {/* View Mode Toggle (Desktop & Tablet) */}
            <div className="hidden sm:flex items-center bg-surface-secondary border border-border-primary rounded-xl p-1">
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`p-1 rounded-lg transition-colors cursor-pointer ${viewMode === 'table' ? 'bg-surface text-tx-primary shadow-xs font-semibold' : 'text-tx-muted hover:text-tx-primary'}`}
                title="Table View"
                aria-label="Table View"
              >
                <List className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                className={`p-1 rounded-lg transition-colors cursor-pointer ${viewMode === 'cards' ? 'bg-surface text-tx-primary shadow-xs font-semibold' : 'text-tx-muted hover:text-tx-primary'}`}
                title="Card View"
                aria-label="Card View"
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
            </div>

            {/* Clear All Filters Button */}
            {activeFiltersCount > 0 && (
              <button
                type="button"
                onClick={resetAllFilters}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-medium text-accent-red hover:bg-accent-red/10 border border-accent-red/20 transition-colors cursor-pointer"
                title="Reset all active filters"
              >
                <X className="w-3 h-3" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* ACTIVE FILTER CHIPS ROW */}
        {activeChips.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border-primary/40">
            <span className="text-xs text-tx-muted font-medium">Active Filters:</span>
            {activeChips.map((chip) => (
              <span
                key={chip.id}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-accent-green/10 text-accent-green border border-accent-green/20"
              >
                <span>{chip.label}</span>
                <button
                  type="button"
                  onClick={chip.onRemove}
                  className="hover:text-accent-red p-0.5 rounded-full cursor-pointer transition-colors"
                  title={`Remove filter: ${chip.label}`}
                  aria-label={`Remove filter: ${chip.label}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            <button
              type="button"
              onClick={resetAllFilters}
              className="text-xs text-tx-secondary hover:text-accent-red underline transition-colors cursor-pointer ml-1"
            >
              Reset All
            </button>
          </div>
        )}

        {/* Filter status label */}
        <div className="flex items-center justify-between text-xs text-tx-secondary pt-2 border-t border-border-primary/40">
          <span>
            Displaying <strong className="text-tx-primary font-mono">{filteredAndSortedStocks.length}</strong> of{' '}
            <strong className="text-tx-primary font-mono">{rawStocks.length}</strong> stocks
          </span>
          {activeFiltersCount > 0 && (
            <span className="text-accent-green font-medium">
              {activeFiltersCount} filter criteria applied
            </span>
          )}
        </div>
      </section>

      {/* 4. STOCK LIST CONTENT AREA */}
      <section aria-label="Stock screener universe list">
        {stocksState.loading ? (
          <div className="bg-surface rounded-2xl border border-border-primary p-12 shadow-sm">
            <LoadingState message="Loading stock universe and calculating indicators..." />
          </div>
        ) : stocksState.error ? (
          <div className="bg-surface rounded-2xl border border-border-primary p-8 shadow-sm">
            <ErrorState
              title="Could not load stock list"
              message={stocksState.error}
              onRetry={handleRefresh}
            />
          </div>
        ) : rawStocks.length === 0 ? (
          <div className="bg-surface rounded-2xl border border-border-primary p-12 shadow-sm">
            <EmptyState message="No stocks currently available in the universe." />
          </div>
        ) : filteredAndSortedStocks.length === 0 ? (
          <div className="bg-surface rounded-2xl border border-border-primary p-12 text-center shadow-sm space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full bg-surface-secondary text-tx-muted flex items-center justify-center">
              <SlidersHorizontal className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-tx-primary mb-1">No matching stocks found</h3>
              <p className="text-xs text-tx-secondary max-w-md mx-auto">
                No stocks match your filter criteria. Stocks with insufficient historical data are strictly excluded from technical indicator filters. Try relaxing criteria or clearing active filters.
              </p>
            </div>
            <button
              type="button"
              onClick={resetAllFilters}
              className="px-4 py-2 bg-surface-secondary border border-border-primary rounded-xl text-xs font-semibold text-tx-primary hover:bg-surface-secondary/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green transition-colors cursor-pointer"
            >
              Clear All Filters
            </button>
          </div>
        ) : (
          <>
            {/* TABLE VIEW */}
            <div className={viewMode === 'table' ? 'block' : 'hidden sm:hidden'}>
              <div className="bg-surface rounded-2xl border border-border-primary shadow-sm overflow-hidden transition-colors">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm border-collapse">
                    <thead>
                      <tr className="bg-surface-secondary/60 text-tx-secondary font-semibold text-xs tracking-wider border-b border-border-primary">
                        <th scope="col" className="px-5 py-3.5">STOCK</th>
                        <th scope="col" className="px-4 py-3.5">SECTOR</th>
                        <th scope="col" className="px-4 py-3.5">PRICE</th>
                        <th scope="col" className="px-4 py-3.5">CHANGE</th>
                        <th scope="col" className="px-4 py-3.5">OPPORTUNITY SCORE</th>
                        <th scope="col" className="px-4 py-3.5">TECHNICAL INDICATORS</th>
                        <th scope="col" className="px-4 py-3.5">SIGNAL</th>
                        <th scope="col" className="px-4 py-3.5">STATUS</th>
                        <th scope="col" className="px-4 py-3.5 text-right">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-primary">
                      {filteredAndSortedStocks.map((stock, idx) => {
                        const priceChange = stock.change_percent ?? stock.price_change_percent;
                        const hasChange = priceChange != null && !isNaN(priceChange);
                        const isPosChange = hasChange ? Number(priceChange) >= 0 : null;
                        const technicals = technicalsMap[stock.symbol];

                        return (
                          <tr
                            key={stock.symbol || idx}
                            className="hover:bg-surface-secondary/50 transition-colors group"
                          >
                            {/* Symbol & Company Name */}
                            <td className="px-5 py-4">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xs font-mono font-medium text-tx-muted w-6 shrink-0">
                                  {idx + 1}
                                </span>
                                <WatchlistButton stock={stock} size="sm" />
                                <div>
                                  <Link
                                    to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                                    className="font-heading font-bold text-base text-tx-primary hover:text-accent-green inline-flex items-center gap-1 transition-colors"
                                  >
                                    {stock.symbol}
                                    <ArrowUpRight className="w-3.5 h-3.5 opacity-50 group-hover:opacity-100 transition-opacity" />
                                  </Link>
                                  <div className="text-xs text-tx-secondary truncate max-w-[200px]" title={stock.company_name}>
                                    {stock.company_name || '—'}
                                  </div>
                                  {stock.industry && (
                                    <div className="text-[10px] text-tx-muted truncate max-w-[180px]">
                                      {stock.industry}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </td>

                            {/* Sector */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              {stock.sector ? (
                                <span className="inline-block text-xs text-tx-secondary font-medium px-2 py-0.5 bg-surface-secondary rounded-md border border-border-primary/50">
                                  {stock.sector}
                                </span>
                              ) : (
                                <span className="text-xs text-tx-secondary">—</span>
                              )}
                            </td>

                            {/* Current / Reference Price */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <span className="font-mono font-semibold text-tx-primary text-sm">
                                {formatCurrency(stock.current_price)}
                              </span>
                            </td>

                            {/* Price Change */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              {hasChange ? (
                                <span className={`inline-flex items-center gap-0.5 text-xs font-mono font-semibold px-2 py-0.5 rounded ${isPosChange ? 'text-accent-green bg-accent-green/10' : 'text-accent-red bg-accent-red/10'}`}>
                                  {isPosChange ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                  {isPosChange ? '+' : ''}{Number(priceChange).toFixed(2)}%
                                </span>
                              ) : (
                                <span className="text-xs text-tx-secondary">—</span>
                              )}
                            </td>

                            {/* Opportunity Score */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <ScoreBadge score={stock.opportunity_score} />
                            </td>

                            {/* Technical Indicators Cell */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <TechnicalIndicatorCell technicals={technicals} />
                            </td>

                            {/* Recommendation / Signal */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <RecommendationBadge recommendation={stock.recommendation} />
                            </td>

                            {/* Market Status */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1.5 text-xs text-tx-secondary">
                                <span className="w-1.5 h-1.5 rounded-full bg-accent-green" />
                                {stock.market_status || 'Active'}
                              </span>
                            </td>

                            {/* Details Action */}
                            <td className="px-4 py-4 whitespace-nowrap text-right">
                              <div className="inline-flex items-center gap-1.5">
                                <Link
                                  to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-secondary border border-border-primary hover:bg-surface-secondary/80 hover:text-accent-green text-tx-primary text-xs font-medium transition-colors"
                                >
                                  <span>Analyze</span>
                                  <ArrowUpRight className="w-3.5 h-3.5" />
                                </Link>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="p-4 border-t border-border-primary bg-surface-secondary/30 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-tx-secondary">
                  <span>
                    Indian Equities Universe · Technical Indicators Computed from Daily OHLCV
                  </span>
                  <span className="font-mono text-[11px]">
                    Non-fabricated Analysis · NSE / BSE
                  </span>
                </div>
              </div>
            </div>

            {/* CARD VIEW (For mobile screens or when card view is toggled) */}
            <div className={viewMode === 'cards' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6' : 'grid sm:hidden grid-cols-1 gap-4'}>
              {filteredAndSortedStocks.map((stock, idx) => {
                const priceChange = stock.change_percent ?? stock.price_change_percent;
                const hasChange = priceChange != null && !isNaN(priceChange);
                const isPosChange = hasChange ? Number(priceChange) >= 0 : null;
                const technicals = technicalsMap[stock.symbol];

                return (
                  <div
                    key={stock.symbol || idx}
                    className="bg-surface rounded-2xl border border-border-primary shadow-sm p-5 hover:border-border-primary/80 transition-all flex flex-col justify-between space-y-4"
                  >
                    <div>
                      {/* Top Row: Symbol, Company Name, Recommendation */}
                      <div className="flex justify-between items-start gap-2 mb-2">
                        <div>
                          <Link
                            to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                            className="font-heading font-bold text-lg text-tx-primary hover:text-accent-green inline-flex items-center gap-1 transition-colors"
                          >
                            {stock.symbol}
                            <ArrowUpRight className="w-4 h-4 opacity-60" />
                          </Link>
                          <div className="text-xs text-tx-secondary truncate max-w-[200px]" title={stock.company_name}>
                            {stock.company_name || '—'}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <WatchlistButton stock={stock} size="sm" />
                          <RecommendationBadge recommendation={stock.recommendation} />
                        </div>
                      </div>

                      {/* Sector & Industry */}
                      <div className="flex items-center gap-2 mb-4 flex-wrap">
                        {stock.sector && (
                          <span className="text-[11px] text-tx-secondary font-medium px-2 py-0.5 bg-surface-secondary rounded-md border border-border-primary/40">
                            {stock.sector}
                          </span>
                        )}
                        {stock.industry && (
                          <span className="text-[10px] text-tx-muted font-normal">
                            {stock.industry}
                          </span>
                        )}
                      </div>

                      {/* Price & Change Banner */}
                      <div className="flex justify-between items-baseline p-3 rounded-xl bg-surface-secondary/40 border border-border-primary/50 mb-3">
                        <div>
                          <span className="text-[11px] text-tx-muted uppercase tracking-wider block">Price</span>
                          <span className="font-mono font-bold text-base text-tx-primary">
                            {formatCurrency(stock.current_price)}
                          </span>
                        </div>
                        {hasChange && (
                          <div className="text-right">
                            <span className={`inline-flex items-center gap-0.5 text-xs font-mono font-semibold px-2 py-0.5 rounded ${isPosChange ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'}`}>
                              {isPosChange ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                              {isPosChange ? '+' : ''}{Number(priceChange).toFixed(2)}%
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Technical Indicators Row */}
                      <div className="p-3 rounded-xl bg-surface-secondary/20 border border-border-primary/40 mb-3 space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-tx-secondary font-medium">Technicals:</span>
                          <TechnicalIndicatorCell technicals={technicals} compact={true} />
                        </div>
                      </div>

                      {/* Scores & Status Breakdown */}
                      <div className="space-y-2 mb-2 text-xs">
                        <div className="flex justify-between items-center">
                          <span className="text-tx-secondary">Opportunity Score</span>
                          <ScoreBadge score={stock.opportunity_score} />
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-tx-secondary">Data Status</span>
                          <span className="inline-flex items-center gap-1.5 text-tx-secondary font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-accent-green" />
                            {stock.market_status || 'Active'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Card Footer */}
                    <div className="pt-2 border-t border-border-primary/50">
                      <Link
                        to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                        className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-surface-secondary hover:bg-surface-secondary/80 hover:text-accent-green border border-border-primary text-tx-primary text-xs font-semibold transition-colors"
                      >
                        <span>View Intelligence Report</span>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </section>

      {/* 5. SLIDE-OVER SCREENER FILTER DRAWER */}
      <ScreenerFilterDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        filters={filters}
        onFilterChange={setFilters}
        onResetFilters={resetAllFilters}
        uniqueSectors={uniqueSectors}
        matchCount={filteredAndSortedStocks.length}
        totalCount={rawStocks.length}
      />
    </div>
  );
};

export default StockExplorer;
