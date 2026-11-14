/**
 * @file Watchlist.jsx
 * @description Phase 17 Watchlist & Stock Tracking page.
 *
 * FEATURES:
 *   - Saved stock list with live universe price merge, daily change, and trend sparkline
 *   - Search saved stocks by symbol or company name
 *   - Filter by All, Gainers, and Decliners
 *   - Sort by Symbol, Price, Daily Change, and Performance Since Added
 *   - Individual stock removal and clear-all with confirmation
 *   - Direct navigation to /stocks/:symbol
 *   - Quick-add stock combobox directly from universe
 *   - Responsive Table and Card presentations consistent with Stock Explorer
 *   - Comprehensive Loading, Error, Empty Watchlist, and Unavailable Data states
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Star,
  Search,
  ArrowUpDown,
  ArrowUpRight,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  X,
  Plus,
  LayoutGrid,
  List,
  AlertCircle,
  Sparkles,
  BarChart2,
  Trash2,
  Activity,
  Check,
} from 'lucide-react';
import { getStocks, getStockHistory } from '../services/api';
import { useWatchlist } from '../hooks/useWatchlist';
import MetricCard from '../components/MetricCard';
import WatchlistButton from '../components/WatchlistButton';
import { LoadingState, ErrorState } from '../components/StateComponents';
import { formatCurrency, formatPercent } from '../utils/formatters';
import {
  calculatePerformanceSinceAdded,
  filterWatchlist,
  sortWatchlist,
} from '../utils/watchlistStorage';

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
  const rec = String(recommendation).toUpperCase();
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
      Watch
    </span>
  );
};

/**
 * Lightweight SVG sparkline visualizing recent trend.
 */
const MiniSparkline = ({ history, isPositive, width = 72, height = 24 }) => {
  if (!Array.isArray(history) || history.length < 2) {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] text-tx-muted font-mono">
        {isPositive ? (
          <TrendingUp className="w-3.5 h-3.5 text-accent-green" />
        ) : isPositive === false ? (
          <TrendingDown className="w-3.5 h-3.5 text-accent-red" />
        ) : (
          <Activity className="w-3.5 h-3.5 text-tx-muted" />
        )}
        <span>{isPositive ? 'Uptrend' : isPositive === false ? 'Downtrend' : 'Flat'}</span>
      </span>
    );
  }

  // Extract closing prices (slice last 14 bars for crisp visual)
  const prices = history
    .slice(-14)
    .map((d) => (d.close != null ? Number(d.close) : Number(d.price || 0)))
    .filter((p) => !isNaN(p) && p > 0);

  if (prices.length < 2) {
    return <span className="text-xs text-tx-muted">—</span>;
  }

  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const padding = 2;
  const drawHeight = height - padding * 2;
  const stepX = (width - padding * 2) / (prices.length - 1);

  const points = prices.map((price, idx) => {
    const x = padding + idx * stepX;
    const y = height - padding - ((price - min) / range) * drawHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = `M ${points.join(' L ')}`;
  const strokeColor = isPositive
    ? '#10B981'
    : isPositive === false
      ? '#EF4444'
      : '#94A3B8';

  return (
    <div className="flex items-center gap-1.5" title={`Recent trend: ${prices.length} bars`}>
      <svg
        width={width}
        height={height}
        className="overflow-visible"
        aria-hidden="true"
      >
        <path
          d={pathD}
          fill="none"
          stroke={strokeColor}
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {isPositive ? (
        <TrendingUp className="w-3 h-3 text-accent-green shrink-0" />
      ) : isPositive === false ? (
        <TrendingDown className="w-3 h-3 text-accent-red shrink-0" />
      ) : null}
    </div>
  );
};

export default function Watchlist() {
  const { watchlist, addToWatchlist, clearWatchlist } = useWatchlist();

  // Universe state from API
  const [universeState, setUniverseState] = useState({
    stocks: [],
    loading: true,
    error: null,
  });

  // History cache for trend sparklines
  const [historyMap, setHistoryMap] = useState({});
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Search, filter, sort & view state
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'GAINERS' | 'DECLINERS'
  const [sortBy, setSortBy] = useState('symbol-asc');
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'cards'

  // Quick-add search combobox state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);
  const [addSearchQuery, setAddSearchQuery] = useState('');

  // Load history for sparklines when stocks or watchlist updates
  useEffect(() => {
    if (watchlist.length === 0) return;
    let active = true;

    const topSymbols = watchlist.slice(0, 8).map((w) => w.symbol);
    for (const sym of topSymbols) {
      if (!historyMap[sym]) {
        getStockHistory(sym)
          .then((hist) => {
            if (active && Array.isArray(hist)) {
              setHistoryMap((prev) => ({ ...prev, [sym]: hist }));
            }
          })
          .catch(() => {});
      }
    }

    return () => {
      active = false;
    };
  }, [watchlist, historyMap]);

  // Initial universe fetch
  useEffect(() => {
    let active = true;

    getStocks()
      .then((data) => {
        if (!active) return;
        const stocksList = Array.isArray(data) ? data : [];
        setUniverseState({
          stocks: stocksList,
          loading: false,
          error: null,
        });
        setLastRefreshed(new Date());
      })
      .catch((err) => {
        if (!active) return;
        setUniverseState({
          stocks: [],
          loading: false,
          error: err.message || 'Failed to load stock universe data.',
        });
      });

    return () => {
      active = false;
    };
  }, []);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const data = await getStocks();
      const stocksList = Array.isArray(data) ? data : [];
      setUniverseState({
        stocks: stocksList,
        loading: false,
        error: null,
      });
      setLastRefreshed(new Date());
    } catch (err) {
      setUniverseState({
        stocks: [],
        loading: false,
        error: err.message || 'Failed to load stock universe data.',
      });
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Merge Watchlist with Universe stock info
  const mergedWatchlist = useMemo(() => {
    const universeLookup = new Map();
    for (const stock of universeState.stocks) {
      if (stock.symbol) {
        universeLookup.set(stock.symbol.toUpperCase(), stock);
      }
    }

    return watchlist.map((item) => {
      const sym = (item.symbol || '').toUpperCase();
      const liveData = universeLookup.get(sym);

      const currentPrice = liveData?.current_price ?? liveData?.price ?? null;
      const changePercent = liveData?.change_percent ?? liveData?.price_change_percent ?? null;
      const perfSinceAdded = calculatePerformanceSinceAdded(currentPrice, item.addedPrice);

      return {
        ...item,
        symbol: sym,
        company_name: liveData?.company_name || item.company_name || sym,
        sector: liveData?.sector || item.sector || '—',
        industry: liveData?.industry || '',
        current_price: currentPrice,
        change_percent: changePercent,
        opportunity_score: liveData?.opportunity_score ?? null,
        recommendation: liveData?.recommendation ?? null,
        market_status: liveData?.market_status || 'Active',
        perfSinceAdded,
        isUnavailable: !liveData && !universeState.loading,
      };
    });
  }, [watchlist, universeState.stocks, universeState.loading]);

  // Filter & Sort
  const filteredAndSortedWatchlist = useMemo(() => {
    const filtered = filterWatchlist(mergedWatchlist, { search, filter });
    return sortWatchlist(filtered, sortBy);
  }, [mergedWatchlist, search, filter, sortBy]);

  // Summary Metrics calculations
  const summaryMetrics = useMemo(() => {
    const total = mergedWatchlist.length;
    let gainers = 0;
    let decliners = 0;
    let totalPerf = 0;
    let perfCount = 0;

    for (const item of mergedWatchlist) {
      const chg = item.change_percent;
      if (chg != null && !isNaN(Number(chg))) {
        if (Number(chg) > 0) gainers++;
        else if (Number(chg) < 0) decliners++;
      }

      if (item.perfSinceAdded != null && !isNaN(item.perfSinceAdded)) {
        totalPerf += item.perfSinceAdded;
        perfCount++;
      }
    }

    const avgPerf = perfCount > 0 ? totalPerf / perfCount : null;

    return { total, gainers, decliners, avgPerf, perfCount };
  }, [mergedWatchlist]);

  // Candidates for Quick-Add Combobox
  const addCandidates = useMemo(() => {
    if (!addSearchQuery.trim()) {
      return universeState.stocks.slice(0, 10);
    }
    const q = addSearchQuery.trim().toLowerCase();
    return universeState.stocks
      .filter((s) => {
        return (
          (s.symbol || '').toLowerCase().includes(q) ||
          (s.company_name || '').toLowerCase().includes(q)
        ) && !watchlist.some((w) => w.symbol === s.symbol);
      })
      .slice(0, 12);
  }, [universeState.stocks, addSearchQuery, watchlist]);

  // Suggested starters for empty watchlist
  const suggestedStarters = useMemo(() => {
    return universeState.stocks
      .filter((s) => s.opportunity_score != null)
      .sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0))
      .slice(0, 3);
  }, [universeState.stocks]);

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 animate-fade-in">
      {/* 1. HEADER SECTION */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-heading font-bold text-2xl sm:text-3xl text-tx-primary tracking-tight">
              Watchlist
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-400/10 text-amber-500 dark:text-amber-400 border border-amber-400/20 inline-flex items-center gap-1 font-mono">
              <Star className="w-3 h-3 fill-amber-400 text-amber-500" />
              <span>{watchlist.length} {watchlist.length === 1 ? 'Stock' : 'Stocks'}</span>
            </span>
          </div>
          <p className="text-tx-secondary text-xs sm:text-sm mt-1">
            Track selected stocks, monitor real-time price updates, and measure performance since added.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 flex-wrap sm:flex-nowrap">
          <div className="text-right hidden sm:block">
            <div className="text-[11px] text-tx-secondary">Last updated</div>
            <div className="text-xs font-mono font-medium text-tx-primary">
              {lastRefreshed ? lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
            </div>
          </div>

          {watchlist.length > 0 && (
            <button
              type="button"
              onClick={() => setIsClearModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-border-primary hover:border-accent-red/40 hover:bg-accent-red/10 hover:text-accent-red text-tx-secondary text-xs font-medium transition-colors cursor-pointer"
              title="Clear all saved stocks"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Clear All</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsAddModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-accent-green hover:bg-accent-green/90 text-surface text-xs sm:text-sm font-semibold transition-colors shadow-xs cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
          >
            <Plus className="w-4 h-4" />
            <span>Add Stock</span>
          </button>

          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing || universeState.loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface border border-border-primary hover:bg-surface-secondary text-tx-primary text-xs sm:text-sm font-medium transition-colors shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green disabled:opacity-50 cursor-pointer"
            title="Refresh prices"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-accent-green ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* 2. SUMMARY METRIC CARDS */}
      <section aria-labelledby="watchlist-metrics-heading">
        <h2 id="watchlist-metrics-heading" className="sr-only">Watchlist Metrics Summary</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <MetricCard
            title="Tracked Stocks"
            value={watchlist.length.toString()}
            subtitle="Saved in watchlist"
            loading={universeState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-amber-400/10 text-amber-500 flex items-center justify-center">
                <Star className="w-5 h-5 fill-amber-400 text-amber-500" />
              </div>
            }
          />

          <MetricCard
            title="Gainers Today"
            value={universeState.loading ? '—' : summaryMetrics.gainers.toString()}
            subtitle={summaryMetrics.total > 0 ? `${((summaryMetrics.gainers / summaryMetrics.total) * 100).toFixed(0)}% of watchlist` : '0%'}
            isPositive={true}
            loading={universeState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                <TrendingUp className="w-5 h-5" />
              </div>
            }
          />

          <MetricCard
            title="Decliners Today"
            value={universeState.loading ? '—' : summaryMetrics.decliners.toString()}
            subtitle="Negative daily change"
            isPositive={summaryMetrics.decliners === 0 ? null : false}
            loading={universeState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-red/10 text-accent-red flex items-center justify-center">
                <TrendingDown className="w-5 h-5" />
              </div>
            }
          />

          <MetricCard
            title="Avg Return Since Added"
            value={
              universeState.loading
                ? '—'
                : summaryMetrics.avgPerf != null
                  ? formatPercent(summaryMetrics.avgPerf)
                  : '—'
            }
            subtitle={summaryMetrics.perfCount > 0 ? `Across ${summaryMetrics.perfCount} priced stocks` : 'Baseline price pending'}
            isPositive={
              summaryMetrics.avgPerf != null
                ? summaryMetrics.avgPerf >= 0
                : null
            }
            loading={universeState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-teal/10 text-accent-teal flex items-center justify-center">
                <Activity className="w-5 h-5" />
              </div>
            }
          />
        </div>
      </section>

      {/* 3. CONTROLS BAR: SEARCH, FILTER PILLS, SORT & VIEW TOGGLE */}
      {watchlist.length > 0 && (
        <section className="bg-surface rounded-2xl border border-border-primary shadow-sm p-4 sm:p-5 transition-colors space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-tx-muted" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search saved stocks by symbol or company name..."
                className="w-full pl-9 pr-9 py-2 bg-surface-secondary border border-border-primary rounded-xl text-tx-primary text-xs sm:text-sm placeholder:text-tx-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green transition-all"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-tx-muted hover:text-tx-primary p-0.5 rounded cursor-pointer"
                  title="Clear search"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Controls Right Side */}
            <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs sm:text-sm">
              {/* Filter Pills (All / Gainers / Decliners) */}
              <div className="inline-flex items-center p-1 bg-surface-secondary border border-border-primary rounded-xl">
                <button
                  type="button"
                  onClick={() => setFilter('ALL')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    filter === 'ALL'
                      ? 'bg-surface text-tx-primary shadow-xs'
                      : 'text-tx-secondary hover:text-tx-primary'
                  }`}
                >
                  All ({watchlist.length})
                </button>
                <button
                  type="button"
                  onClick={() => setFilter('GAINERS')}
                  className={`inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    filter === 'GAINERS'
                      ? 'bg-accent-green/15 text-accent-green shadow-xs'
                      : 'text-tx-secondary hover:text-tx-primary'
                  }`}
                >
                  <TrendingUp className="w-3 h-3" />
                  <span>Gainers ({summaryMetrics.gainers})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setFilter('DECLINERS')}
                  className={`inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    filter === 'DECLINERS'
                      ? 'bg-accent-red/15 text-accent-red shadow-xs'
                      : 'text-tx-secondary hover:text-tx-primary'
                  }`}
                >
                  <TrendingDown className="w-3 h-3" />
                  <span>Decliners ({summaryMetrics.decliners})</span>
                </button>
              </div>

              {/* Sort By Dropdown */}
              <div className="flex items-center gap-1.5 bg-surface-secondary border border-border-primary rounded-xl px-2.5 py-1.5">
                <ArrowUpDown className="w-3.5 h-3.5 text-tx-muted shrink-0" />
                <label htmlFor="watchlist-sort" className="sr-only">Sort watchlist</label>
                <select
                  id="watchlist-sort"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-transparent text-tx-primary text-xs font-medium focus:outline-none cursor-pointer"
                >
                  <option value="symbol-asc">Symbol (A → Z)</option>
                  <option value="symbol-desc">Symbol (Z → A)</option>
                  <option value="price-desc">Price: High to Low</option>
                  <option value="price-asc">Price: Low to High</option>
                  <option value="change-desc">Daily Change: Highest First</option>
                  <option value="change-asc">Daily Change: Lowest First</option>
                  <option value="perf-desc">Return Since Added: Highest First</option>
                  <option value="perf-asc">Return Since Added: Lowest First</option>
                  <option value="added-desc">Recently Added</option>
                  <option value="added-asc">Oldest Added</option>
                  <option value="score-desc">Opportunity Score</option>
                </select>
              </div>

              {/* View Mode Toggle (Table vs Cards) */}
              <div className="hidden sm:inline-flex items-center p-1 bg-surface-secondary border border-border-primary rounded-xl">
                <button
                  type="button"
                  onClick={() => setViewMode('table')}
                  aria-label="Table view"
                  title="Table view"
                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                    viewMode === 'table'
                      ? 'bg-surface text-tx-primary shadow-xs'
                      : 'text-tx-muted hover:text-tx-primary'
                  }`}
                >
                  <List className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('cards')}
                  aria-label="Card grid view"
                  title="Card grid view"
                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                    viewMode === 'cards'
                      ? 'bg-surface text-tx-primary shadow-xs'
                      : 'text-tx-muted hover:text-tx-primary'
                  }`}
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 4. MAIN CONTENT AREA */}
      {universeState.loading && watchlist.length > 0 ? (
        <LoadingState message="Connecting to market universe data..." className="min-h-[360px]" />
      ) : universeState.error ? (
        <ErrorState
          title="Market Data Error"
          message={universeState.error}
          onRetry={handleRefresh}
          className="min-h-[300px]"
        />
      ) : watchlist.length === 0 ? (
        /* EMPTY WATCHLIST STATE */
        <div className="bg-surface rounded-2xl border border-border-primary p-8 sm:p-12 text-center max-w-2xl mx-auto shadow-sm space-y-6 animate-fade-in">
          <div className="w-16 h-16 rounded-2xl bg-amber-400/10 text-amber-500 border border-amber-400/20 flex items-center justify-center mx-auto">
            <Star className="w-8 h-8 fill-amber-400 text-amber-500 drop-shadow-[0_0_10px_rgba(251,191,36,0.4)]" />
          </div>

          <div>
            <h3 className="font-heading font-bold text-xl sm:text-2xl text-tx-primary tracking-tight">
              Your Watchlist is Empty
            </h3>
            <p className="text-tx-secondary text-xs sm:text-sm mt-2 max-w-md mx-auto">
              Save stocks you want to monitor closely. You can add stocks from the Stock Explorer, Stock Detail reports, or quick-add from top swing opportunities below.
            </p>
          </div>

          {/* Quick Start Suggestions */}
          {suggestedStarters.length > 0 && (
            <div className="pt-2 text-left">
              <div className="text-xs font-semibold uppercase tracking-wider text-tx-muted mb-3 text-center">
                Top Rated Suggestions to Start Your Watchlist
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {suggestedStarters.map((s) => (
                  <div
                    key={s.symbol}
                    className="p-3.5 rounded-xl border border-border-primary bg-surface-secondary/50 flex flex-col justify-between hover:border-accent-green/40 transition-colors"
                  >
                    <div>
                      <div className="flex justify-between items-start mb-1">
                        <Link
                          to={`/stocks/${encodeURIComponent(s.symbol)}`}
                          className="font-bold text-sm text-tx-primary hover:text-accent-green font-mono"
                        >
                          {s.symbol}
                        </Link>
                        <span className="text-[10px] font-mono font-semibold px-1.5 py-0.2 rounded bg-accent-green/10 text-accent-green">
                          Score {s.opportunity_score}
                        </span>
                      </div>
                      <div className="text-[11px] text-tx-secondary truncate mb-2">
                        {s.company_name}
                      </div>
                      <div className="text-xs font-mono font-semibold text-tx-primary">
                        {formatCurrency(s.current_price)}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => addToWatchlist(s)}
                      className="mt-3 w-full inline-flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg bg-surface border border-border-primary hover:bg-amber-400/10 hover:border-amber-400/40 text-tx-primary text-xs font-medium transition-colors cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5 text-amber-500" />
                      <span>Add to Watchlist</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-center gap-3 pt-4 border-t border-border-primary">
            <Link
              to="/stocks"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-green text-surface text-xs sm:text-sm font-semibold hover:bg-accent-green/90 transition-colors shadow-xs"
            >
              <BarChart2 className="w-4 h-4" />
              <span>Explore All Stocks</span>
            </Link>
            <Link
              to="/opportunities"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-secondary border border-border-primary text-tx-primary text-xs sm:text-sm font-semibold hover:bg-surface-secondary/80 transition-colors"
            >
              <Sparkles className="w-4 h-4 text-accent-green" />
              <span>View Swing Opportunities</span>
            </Link>
          </div>
        </div>
      ) : filteredAndSortedWatchlist.length === 0 ? (
        /* NO RESULTS MATCHING FILTER */
        <div className="bg-surface rounded-2xl border border-border-primary p-8 sm:p-12 text-center shadow-sm space-y-4">
          <AlertCircle className="w-10 h-10 text-tx-muted mx-auto" />
          <div>
            <h3 className="font-heading font-semibold text-lg text-tx-primary">No Matching Stocks Found</h3>
            <p className="text-xs text-tx-secondary mt-1">
              No saved stocks in your watchlist match "{search || filter}".
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setSearch('');
              setFilter('ALL');
            }}
            className="px-4 py-2 rounded-xl bg-surface-secondary border border-border-primary text-xs font-semibold text-tx-primary hover:bg-surface-secondary/80 transition-colors cursor-pointer"
          >
            Clear Filters
          </button>
        </div>
      ) : (
        /* WATCHLIST PRESENTATION */
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
                      <th scope="col" className="px-4 py-3.5">LATEST PRICE</th>
                      <th scope="col" className="px-4 py-3.5">DAILY CHANGE</th>
                      <th scope="col" className="px-4 py-3.5">TREND</th>
                      <th scope="col" className="px-4 py-3.5">RETURN SINCE ADDED</th>
                      <th scope="col" className="px-4 py-3.5">SCORE</th>
                      <th scope="col" className="px-4 py-3.5">SIGNAL</th>
                      <th scope="col" className="px-4 py-3.5 text-right">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-primary">
                    {filteredAndSortedWatchlist.map((stock, idx) => {
                      const hasPrice = stock.current_price != null && !isNaN(Number(stock.current_price));
                      const priceChange = stock.change_percent;
                      const hasChange = priceChange != null && !isNaN(Number(priceChange));
                      const isPosChange = hasChange ? Number(priceChange) >= 0 : null;
                      const hasPerf = stock.perfSinceAdded != null;
                      const isPosPerf = hasPerf ? stock.perfSinceAdded >= 0 : null;
                      const history = historyMap[stock.symbol];

                      return (
                        <tr
                          key={stock.symbol || idx}
                          className="hover:bg-surface-secondary/50 transition-colors group"
                        >
                          {/* Symbol & Company Name */}
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-3">
                              <WatchlistButton stock={stock} size="sm" />
                              <div>
                                <Link
                                  to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                                  className="font-heading font-bold text-base text-tx-primary hover:text-accent-green inline-flex items-center gap-1 transition-colors"
                                >
                                  {stock.symbol}
                                  <ArrowUpRight className="w-3.5 h-3.5 opacity-50 group-hover:opacity-100 transition-opacity" />
                                </Link>
                                <div className="text-xs text-tx-secondary truncate max-w-[180px]" title={stock.company_name}>
                                  {stock.company_name || '—'}
                                </div>
                                {stock.isUnavailable && (
                                  <span className="inline-block mt-0.5 px-1.5 py-0.2 rounded text-[10px] font-medium bg-accent-warning/10 text-accent-warning border border-accent-warning/20">
                                    Off-market / Data Pending
                                  </span>
                                )}
                              </div>
                            </div>
                          </td>

                          {/* Sector */}
                          <td className="px-4 py-4 whitespace-nowrap">
                            {stock.sector && stock.sector !== '—' ? (
                              <span className="inline-block text-xs text-tx-secondary font-medium px-2 py-0.5 bg-surface-secondary rounded-md border border-border-primary/50">
                                {stock.sector}
                              </span>
                            ) : (
                              <span className="text-xs text-tx-secondary">—</span>
                            )}
                          </td>

                          {/* Current Price */}
                          <td className="px-4 py-4 whitespace-nowrap">
                            <span className="font-mono font-semibold text-tx-primary text-sm">
                              {hasPrice ? formatCurrency(stock.current_price) : '—'}
                            </span>
                            {stock.addedPrice && (
                              <div className="text-[10px] text-tx-muted font-mono" title="Price when added">
                                Added: {formatCurrency(stock.addedPrice)}
                              </div>
                            )}
                          </td>

                          {/* Daily Change */}
                          <td className="px-4 py-4 whitespace-nowrap">
                            {hasChange ? (
                              <span
                                className={`inline-flex items-center gap-0.5 text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                                  isPosChange
                                    ? 'text-accent-green bg-accent-green/10'
                                    : 'text-accent-red bg-accent-red/10'
                                }`}
                              >
                                {isPosChange ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                {isPosChange ? '+' : ''}{Number(priceChange).toFixed(2)}%
                              </span>
                            ) : (
                              <span className="text-xs text-tx-secondary">—</span>
                            )}
                          </td>

                          {/* Trend Mini-Sparkline */}
                          <td className="px-4 py-4 whitespace-nowrap">
                            <MiniSparkline
                              history={history}
                              isPositive={isPosChange}
                            />
                          </td>

                          {/* Return Since Added */}
                          <td className="px-4 py-4 whitespace-nowrap">
                            {hasPerf ? (
                              <span
                                className={`inline-flex items-center gap-1 font-mono text-xs font-semibold px-2 py-0.5 rounded ${
                                  isPosPerf
                                    ? 'text-accent-green bg-accent-green/10'
                                    : 'text-accent-red bg-accent-red/10'
                                }`}
                              >
                                {isPosPerf ? '+' : ''}{stock.perfSinceAdded.toFixed(2)}%
                              </span>
                            ) : (
                              <span className="text-xs text-tx-muted font-mono" title="Requires initial price">
                                {stock.addedPrice ? '—' : 'Baseline unset'}
                              </span>
                            )}
                          </td>

                          {/* Opportunity Score */}
                          <td className="px-4 py-4 whitespace-nowrap">
                            <ScoreBadge score={stock.opportunity_score} />
                          </td>

                          {/* Recommendation / Signal */}
                          <td className="px-4 py-4 whitespace-nowrap">
                            <RecommendationBadge recommendation={stock.recommendation} />
                          </td>

                          {/* Actions */}
                          <td className="px-4 py-4 whitespace-nowrap text-right">
                            <div className="inline-flex items-center gap-1.5">
                              <Link
                                to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-secondary border border-border-primary hover:bg-surface-secondary/80 hover:text-accent-green text-tx-primary text-xs font-medium transition-colors"
                              >
                                <span>Analyze</span>
                                <ArrowUpRight className="w-3.5 h-3.5" />
                              </Link>
                              <WatchlistButton stock={stock} variant="remove" />
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
                  Showing {filteredAndSortedWatchlist.length} of {watchlist.length} saved stocks
                </span>
                <span className="font-mono text-[11px]">
                  Real-time synchronization · Indian Equities NSE/BSE
                </span>
              </div>
            </div>
          </div>

          {/* CARD VIEW */}
          <div className={viewMode === 'cards' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6' : 'grid sm:hidden grid-cols-1 gap-4'}>
            {filteredAndSortedWatchlist.map((stock, idx) => {
              const hasPrice = stock.current_price != null && !isNaN(Number(stock.current_price));
              const priceChange = stock.change_percent;
              const hasChange = priceChange != null && !isNaN(Number(priceChange));
              const isPosChange = hasChange ? Number(priceChange) >= 0 : null;
              const hasPerf = stock.perfSinceAdded != null;
              const isPosPerf = hasPerf ? stock.perfSinceAdded >= 0 : null;
              const history = historyMap[stock.symbol];

              return (
                <div
                  key={stock.symbol || idx}
                  className="bg-surface rounded-2xl border border-border-primary shadow-sm p-5 hover:border-border-primary/80 transition-all flex flex-col justify-between space-y-4"
                >
                  <div>
                    {/* Card Top: Symbol, Sector, Star Toggle & Remove */}
                    <div className="flex justify-between items-start gap-2 mb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                            className="font-heading font-bold text-lg text-tx-primary hover:text-accent-green inline-flex items-center gap-1 transition-colors"
                          >
                            {stock.symbol}
                            <ArrowUpRight className="w-3.5 h-3.5 opacity-50" />
                          </Link>
                          {stock.sector && stock.sector !== '—' && (
                            <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-surface-secondary text-tx-secondary border border-border-primary/50">
                              {stock.sector}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-tx-secondary truncate max-w-[200px]" title={stock.company_name}>
                          {stock.company_name || '—'}
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <WatchlistButton stock={stock} size="sm" />
                        <WatchlistButton stock={stock} variant="remove" />
                      </div>
                    </div>

                    {/* Price & Daily Change */}
                    <div className="flex items-baseline justify-between mt-3 pt-3 border-t border-border-primary/60">
                      <div>
                        <div className="text-[10px] uppercase font-semibold text-tx-muted">Price</div>
                        <div className="font-heading font-bold text-lg text-tx-primary font-mono">
                          {hasPrice ? formatCurrency(stock.current_price) : '—'}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-[10px] uppercase font-semibold text-tx-muted">Daily Change</div>
                        {hasChange ? (
                          <span
                            className={`inline-flex items-center gap-0.5 text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                              isPosChange
                                ? 'text-accent-green bg-accent-green/10'
                                : 'text-accent-red bg-accent-red/10'
                            }`}
                          >
                            {isPosChange ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                            {isPosChange ? '+' : ''}{Number(priceChange).toFixed(2)}%
                          </span>
                        ) : (
                          <span className="text-xs text-tx-secondary">—</span>
                        )}
                      </div>
                    </div>

                    {/* Trend & Return Since Added */}
                    <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-border-primary/60 text-xs">
                      <div>
                        <div className="text-[10px] uppercase font-semibold text-tx-muted mb-1">Trend</div>
                        <MiniSparkline
                          history={history}
                          isPositive={isPosChange}
                          width={80}
                        />
                      </div>
                      <div className="text-right">
                        <div className="text-[10px] uppercase font-semibold text-tx-muted mb-1">Since Added</div>
                        {hasPerf ? (
                          <span
                            className={`inline-flex items-center gap-0.5 font-mono text-xs font-semibold ${
                              isPosPerf ? 'text-accent-green' : 'text-accent-red'
                            }`}
                          >
                            {isPosPerf ? '+' : ''}{stock.perfSinceAdded.toFixed(2)}%
                          </span>
                        ) : (
                          <span className="text-tx-muted font-mono text-[11px]">
                            {stock.addedPrice ? '—' : 'Unset'}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Card Bottom: Recommendation & Analyze Link */}
                  <div className="pt-3 border-t border-border-primary/60 flex items-center justify-between">
                    <RecommendationBadge recommendation={stock.recommendation} />
                    <Link
                      to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-accent-green hover:underline"
                    >
                      <span>Analyze Intelligence</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* 5. QUICK-ADD STOCK MODAL / COMBOBOX */}
      {isAddModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-stock-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in"
          onClick={() => setIsAddModalOpen(false)}
        >
          <div
            className="bg-surface rounded-2xl border border-border-primary shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center">
              <div>
                <h3 id="add-stock-modal-title" className="font-heading font-bold text-lg text-tx-primary">
                  Add Stock to Watchlist
                </h3>
                <p className="text-xs text-tx-secondary mt-0.5">
                  Search across the covered Indian equities universe
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="p-1 rounded-lg text-tx-muted hover:text-tx-primary transition-colors cursor-pointer"
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-tx-muted" />
              <input
                type="text"
                value={addSearchQuery}
                onChange={(e) => setAddSearchQuery(e.target.value)}
                placeholder="Type symbol (e.g. TCS) or company name..."
                autoFocus
                className="w-full pl-9 pr-9 py-2.5 bg-surface-secondary border border-border-primary rounded-xl text-tx-primary text-sm placeholder:text-tx-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
              />
              {addSearchQuery && (
                <button
                  type="button"
                  onClick={() => setAddSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-tx-muted hover:text-tx-primary p-0.5 rounded cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Candidates list */}
            <div className="flex-1 overflow-y-auto divide-y divide-border-primary/60 pr-1 space-y-1">
              {addCandidates.length === 0 ? (
                <div className="py-8 text-center text-xs text-tx-muted">
                  No unadded stocks match "{addSearchQuery}".
                </div>
              ) : (
                addCandidates.map((candidate) => {
                  const inList = watchlist.some((w) => w.symbol === candidate.symbol);
                  return (
                    <div
                      key={candidate.symbol}
                      className="py-2.5 flex items-center justify-between gap-3 hover:bg-surface-secondary/40 px-2 rounded-xl transition-colors"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-heading font-bold text-sm text-tx-primary font-mono">
                            {candidate.symbol}
                          </span>
                          {candidate.sector && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-surface-secondary text-tx-secondary">
                              {candidate.sector}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-tx-secondary truncate max-w-[220px]">
                          {candidate.company_name}
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <div className="text-right">
                          <div className="text-xs font-mono font-semibold text-tx-primary">
                            {formatCurrency(candidate.current_price)}
                          </div>
                          {candidate.change_percent != null && (
                            <div
                              className={`text-[10px] font-mono font-semibold ${
                                Number(candidate.change_percent) >= 0
                                  ? 'text-accent-green'
                                  : 'text-accent-red'
                              }`}
                            >
                              {Number(candidate.change_percent) >= 0 ? '+' : ''}
                              {Number(candidate.change_percent).toFixed(2)}%
                            </div>
                          )}
                        </div>

                        <button
                          type="button"
                          disabled={inList}
                          onClick={() => {
                            addToWatchlist(candidate);
                          }}
                          className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                            inList
                              ? 'bg-surface-secondary text-tx-muted cursor-not-allowed'
                              : 'bg-accent-green text-surface hover:bg-accent-green/90 shadow-xs'
                          }`}
                        >
                          {inList ? (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              <span>Added</span>
                            </>
                          ) : (
                            <>
                              <Plus className="w-3.5 h-3.5" />
                              <span>Add</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="pt-3 border-t border-border-primary flex justify-end">
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-surface-secondary border border-border-primary text-xs font-semibold text-tx-primary hover:bg-surface-secondary/80 transition-colors cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. CLEAR ALL CONFIRMATION MODAL */}
      {isClearModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="clear-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in"
          onClick={() => setIsClearModalOpen(false)}
        >
          <div
            className="bg-surface rounded-2xl border border-border-primary shadow-xl w-full max-w-sm p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-12 h-12 rounded-2xl bg-accent-red/10 text-accent-red flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>

            <div className="text-center">
              <h3 id="clear-modal-title" className="font-heading font-bold text-lg text-tx-primary">
                Clear Entire Watchlist?
              </h3>
              <p className="text-xs text-tx-secondary mt-1.5">
                This will remove all {watchlist.length} saved stocks from your watchlist. You can always add them back later.
              </p>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsClearModalOpen(false)}
                className="flex-1 py-2 rounded-xl bg-surface-secondary border border-border-primary text-xs font-semibold text-tx-primary hover:bg-surface-secondary/80 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  clearWatchlist();
                  setIsClearModalOpen(false);
                }}
                className="flex-1 py-2 rounded-xl bg-accent-red text-surface text-xs font-semibold hover:bg-accent-red/90 transition-colors shadow-xs cursor-pointer"
              >
                Yes, Clear All
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
