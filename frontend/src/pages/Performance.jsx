/**
 * @file Performance.jsx
 * @description Phase 18 Portfolio & Performance Dashboard.
 *
 * CRITICAL ARCHITECTURAL CONCEPTS:
 *   1. Strictly Separates Two Distinct Categories:
 *      - Algorithmic Strategy Backtest: Simulated quantitative metrics computed from historical trade records.
 *      - Watchlist Forward Tracking: Price changes of user-saved stocks since added, using Phase 17's baseline reference price.
 *      - NEVER combines watchlist returns with backtest returns into one portfolio figure.
 *   2. Non-Fabricated Data:
 *      - Renders Equity Curve, Drawdown, and Monthly Returns ONLY when source series are valid and verified.
 *      - Clearly distinguishes unavailable metrics from zero values.
 *      - Handles loading, error, and empty states gracefully.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Star,
  Activity,
  ArrowUpRight,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Award,
} from 'lucide-react';
import { getLatestBacktest, getStocks } from '../services/api';
import { useWatchlist } from '../hooks/useWatchlist';
import MetricCard from '../components/MetricCard';
import EquityCurveChart from '../charts/EquityCurveChart';
import { LoadingState, ErrorState } from '../components/StateComponents';
import { formatCurrency, formatPercent, formatRatio } from '../utils/formatters';
import {
  calculateWatchlistPortfolioMetrics,
  normalizeBacktestData,
} from '../utils/performanceHelpers';

export default function Performance() {
  const { watchlist } = useWatchlist();

  // Active view tab: 'overview' | 'backtest' | 'watchlist'
  const [activeTab, setActiveTab] = useState('overview');

  // Backtest API state
  const [backtestState, setBacktestState] = useState({
    data: null,
    loading: true,
    error: null,
  });

  // Universe stocks state (for live watchlist pricing)
  const [universeState, setUniverseState] = useState({
    stocks: [],
    loading: true,
    error: null,
  });

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Watchlist filter & search inside Performance page
  const [watchlistSearch, setWatchlistSearch] = useState('');
  const [watchlistFilter, setWatchlistFilter] = useState('ALL'); // 'ALL' | 'GAINERS' | 'DECLINERS'

  // Fetch Backtest Data
  const fetchBacktestData = useCallback(async () => {
    try {
      const res = await getLatestBacktest();
      setBacktestState({
        data: normalizeBacktestData(res),
        loading: false,
        error: null,
      });
    } catch (err) {
      setBacktestState({
        data: null,
        loading: false,
        error: err.message || 'Failed to retrieve backtest performance metrics.',
      });
    }
  }, []);

  // Fetch Universe stocks for watchlist pricing
  const fetchUniverseStocks = useCallback(async () => {
    try {
      const res = await getStocks();
      setUniverseState({
        stocks: Array.isArray(res) ? res : [],
        loading: false,
        error: null,
      });
    } catch (err) {
      setUniverseState({
        stocks: [],
        loading: false,
        error: err.message || 'Failed to load stock universe prices.',
      });
    }
  }, []);

  // Initial load
  useEffect(() => {
    let active = true;

    Promise.allSettled([getLatestBacktest(), getStocks()]).then(([resBacktest, resStocks]) => {
      if (!active) return;

      if (resBacktest.status === 'fulfilled') {
        setBacktestState({
          data: normalizeBacktestData(resBacktest.value),
          loading: false,
          error: null,
        });
      } else {
        setBacktestState({
          data: null,
          loading: false,
          error: resBacktest.reason?.message || 'Failed to load backtest data.',
        });
      }

      if (resStocks.status === 'fulfilled') {
        setUniverseState({
          stocks: Array.isArray(resStocks.value) ? resStocks.value : [],
          loading: false,
          error: null,
        });
      } else {
        setUniverseState({
          stocks: [],
          loading: false,
          error: resStocks.reason?.message || 'Failed to load stock universe.',
        });
      }

      setLastRefreshed(new Date());
    });

    return () => {
      active = false;
    };
  }, []);

  // Manual refresh handler
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([fetchBacktestData(), fetchUniverseStocks()]);
      setLastRefreshed(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchBacktestData, fetchUniverseStocks]);

  // Derived Watchlist Portfolio Metrics
  const watchlistMetrics = useMemo(() => {
    return calculateWatchlistPortfolioMetrics(watchlist, universeState.stocks);
  }, [watchlist, universeState.stocks]);

  // Filtered Watchlist stocks for the table
  const filteredWatchlistStocks = useMemo(() => {
    const query = watchlistSearch.trim().toLowerCase();
    return watchlistMetrics.stocks.filter((s) => {
      if (query) {
        const matchesSym = s.symbol.toLowerCase().includes(query);
        const matchesName = (s.company_name || '').toLowerCase().includes(query);
        if (!matchesSym && !matchesName) return false;
      }
      if (watchlistFilter === 'GAINERS') {
        return s.returnSinceAdded != null && s.returnSinceAdded > 0;
      }
      if (watchlistFilter === 'DECLINERS') {
        return s.returnSinceAdded != null && s.returnSinceAdded < 0;
      }
      return true;
    });
  }, [watchlistMetrics.stocks, watchlistSearch, watchlistFilter]);

  const backtest = backtestState.data;
  const isLoading = backtestState.loading || universeState.loading;

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 animate-fade-in">
      {/* 1. TOP HEADER & CATEGORY NAVIGATION */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-heading font-bold text-2xl sm:text-3xl text-tx-primary tracking-tight">
              Performance & Portfolio Intelligence
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent-teal/10 text-accent-teal border border-accent-teal/20 font-mono">
              Phase 18
            </span>
          </div>
          <p className="text-tx-secondary text-xs sm:text-sm mt-1">
            Algorithmic strategy backtesting analytics alongside non-realized forward watchlist tracking.
          </p>
        </div>

        {/* Header Right Actions */}
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
            disabled={isRefreshing || isLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface border border-border-primary hover:bg-surface-secondary text-tx-primary text-xs sm:text-sm font-medium transition-colors shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green disabled:opacity-50 cursor-pointer"
            title="Refresh performance analytics"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-accent-green ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* 2. DUAL-CATEGORY SEGMENTED TABS */}
      <div className="flex items-center p-1 bg-surface-secondary border border-border-primary rounded-2xl max-w-md">
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl transition-all cursor-pointer text-center ${
            activeTab === 'overview'
              ? 'bg-surface text-tx-primary shadow-xs'
              : 'text-tx-secondary hover:text-tx-primary'
          }`}
        >
          Executive Overview
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('backtest')}
          className={`flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl transition-all cursor-pointer text-center ${
            activeTab === 'backtest'
              ? 'bg-surface text-accent-teal shadow-xs'
              : 'text-tx-secondary hover:text-tx-primary'
          }`}
        >
          Strategy Backtest
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('watchlist')}
          className={`flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl transition-all cursor-pointer text-center ${
            activeTab === 'watchlist'
              ? 'bg-surface text-amber-500 shadow-xs'
              : 'text-tx-secondary hover:text-tx-primary'
          }`}
        >
          Watchlist Tracking ({watchlist.length})
        </button>
      </div>

      {/* 3. LOADING & ERROR STATES */}
      {isLoading ? (
        <LoadingState message="Calculating strategy backtest and watchlist portfolio metrics..." className="min-h-[380px]" />
      ) : backtestState.error && universeState.error ? (
        <ErrorState
          title="Performance Data Retrieval Error"
          message={backtestState.error}
          onRetry={handleRefresh}
          className="min-h-[300px]"
        />
      ) : (
        <>
          {/* ========================================================================= */}
          {/* TAB 1: EXECUTIVE OVERVIEW (Side-by-side executive separation)            */}
          {/* ========================================================================= */}
          {activeTab === 'overview' && (
            <div className="space-y-6 sm:space-y-8 animate-fade-in">
              {/* Category 1 Summary Card: Backtest Strategy */}
              <section className="bg-surface rounded-2xl border border-border-primary p-6 sm:p-7 shadow-sm space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-primary/60 pb-4">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-accent-teal/10 text-accent-teal flex items-center justify-center">
                      <BarChart3 className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="font-heading font-bold text-lg text-tx-primary">
                          Algorithmic Backtest Performance
                        </h2>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-accent-teal/10 text-accent-teal border border-accent-teal/20">
                          Simulated Strategy
                        </span>
                      </div>
                      <p className="text-xs text-tx-secondary">
                        Strategy: <strong className="text-tx-primary">{backtest?.strategy_name}</strong> · Period: {backtest?.period}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setActiveTab('backtest')}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-accent-teal hover:underline self-start sm:self-auto cursor-pointer"
                  >
                    <span>View Full Strategy Analytics</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Backtest Executive Metrics Grid */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="p-4 rounded-xl bg-surface-secondary/40 border border-border-primary/50">
                    <div className="text-[11px] font-semibold text-tx-muted uppercase">Strategy Win Rate</div>
                    <div className="text-xl sm:text-2xl font-heading font-bold text-tx-primary font-mono mt-1">
                      {backtest?.win_rate != null ? `${backtest.win_rate.toFixed(1)}%` : '—'}
                    </div>
                    <div className="text-[11px] text-tx-secondary mt-0.5">
                      {backtest?.winning_trades || 0} Wins / {backtest?.losing_trades || 0} Losses
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-surface-secondary/40 border border-border-primary/50">
                    <div className="text-[11px] font-semibold text-tx-muted uppercase">Total Return / CAGR</div>
                    <div className={`text-xl sm:text-2xl font-heading font-bold font-mono mt-1 ${
                      (backtest?.total_return_pct ?? 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
                    }`}>
                      {backtest?.total_return_pct != null ? formatPercent(backtest.total_return_pct) : '—'}
                    </div>
                    <div className="text-[11px] text-tx-secondary mt-0.5">
                      P&L: {formatCurrency(backtest?.total_pl, { compact: true })}
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-surface-secondary/40 border border-border-primary/50">
                    <div className="text-[11px] font-semibold text-tx-muted uppercase">Profit Factor</div>
                    <div className="text-xl sm:text-2xl font-heading font-bold text-accent-green font-mono mt-1">
                      {backtest?.profit_factor != null ? formatRatio(backtest.profit_factor, { format: 'multiplier' }) : '—'}
                    </div>
                    <div className="text-[11px] text-tx-secondary mt-0.5">
                      Gross profit / gross loss
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-surface-secondary/40 border border-border-primary/50">
                    <div className="text-[11px] font-semibold text-tx-muted uppercase">Max Drawdown</div>
                    <div className="text-xl sm:text-2xl font-heading font-bold text-accent-red font-mono mt-1">
                      {backtest?.max_drawdown_pct != null ? `-${backtest.max_drawdown_pct.toFixed(1)}%` : '—'}
                    </div>
                    <div className="text-[11px] text-tx-secondary mt-0.5">
                      Peak-to-trough decline
                    </div>
                  </div>
                </div>
              </section>

              {/* Category 2 Summary Card: Watchlist Forward Tracking */}
              <section className="bg-surface rounded-2xl border border-border-primary p-6 sm:p-7 shadow-sm space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-primary/60 pb-4">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-amber-400/10 text-amber-500 flex items-center justify-center">
                      <Star className="w-5 h-5 fill-amber-400 text-amber-500" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="font-heading font-bold text-lg text-tx-primary">
                          Watchlist Forward Tracking
                        </h2>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-400/10 text-amber-500 dark:text-amber-400 border border-amber-400/20">
                          Non-Realized
                        </span>
                      </div>
                      <p className="text-xs text-tx-secondary">
                        Hypothetical price tracking since stock was added to watchlist · {watchlistMetrics.totalTracked} saved {watchlistMetrics.totalTracked === 1 ? 'stock' : 'stocks'}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setActiveTab('watchlist')}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-amber-500 hover:underline self-start sm:self-auto cursor-pointer"
                  >
                    <span>Inspect Tracked Positions</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                {watchlistMetrics.totalTracked === 0 ? (
                  <div className="py-6 text-center text-xs text-tx-secondary space-y-2">
                    <p>No stocks currently in your watchlist to track.</p>
                    <Link
                      to="/stocks"
                      className="inline-flex items-center gap-1 font-semibold text-accent-green hover:underline"
                    >
                      <span>Explore Stock Universe</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="p-4 rounded-xl bg-surface-secondary/40 border border-border-primary/50">
                      <div className="text-[11px] font-semibold text-tx-muted uppercase">Tracked Equities</div>
                      <div className="text-xl sm:text-2xl font-heading font-bold text-tx-primary font-mono mt-1">
                        {watchlistMetrics.totalTracked}
                      </div>
                      <div className="text-[11px] text-tx-secondary mt-0.5">
                        {watchlistMetrics.pricedCount} with baseline price
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-surface-secondary/40 border border-border-primary/50">
                      <div className="text-[11px] font-semibold text-tx-muted uppercase">Avg Return Since Added</div>
                      <div className={`text-xl sm:text-2xl font-heading font-bold font-mono mt-1 ${
                        (watchlistMetrics.avgReturnSinceAdded ?? 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
                      }`}>
                        {watchlistMetrics.avgReturnSinceAdded != null
                          ? formatPercent(watchlistMetrics.avgReturnSinceAdded)
                          : '—'}
                      </div>
                      <div className="text-[11px] text-tx-secondary mt-0.5">
                        Across priced watchlist items
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-surface-secondary/40 border border-border-primary/50">
                      <div className="text-[11px] font-semibold text-tx-muted uppercase">Gainers vs Decliners</div>
                      <div className="text-xl sm:text-2xl font-heading font-bold font-mono mt-1 flex items-baseline gap-1.5">
                        <span className="text-accent-green">{watchlistMetrics.gainersCount}▲</span>
                        <span className="text-tx-muted text-sm font-normal">/</span>
                        <span className="text-accent-red">{watchlistMetrics.declinersCount}▼</span>
                      </div>
                      <div className="text-[11px] text-tx-secondary mt-0.5">
                        Since individual addition dates
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-surface-secondary/40 border border-border-primary/50">
                      <div className="text-[11px] font-semibold text-tx-muted uppercase">Top Forward Performer</div>
                      <div className="text-xl sm:text-2xl font-heading font-bold text-accent-green font-mono mt-1 truncate">
                        {watchlistMetrics.bestPerformer ? watchlistMetrics.bestPerformer.symbol : '—'}
                      </div>
                      <div className="text-[11px] text-tx-secondary mt-0.5 truncate">
                        {watchlistMetrics.bestPerformer
                          ? `${formatPercent(watchlistMetrics.bestPerformer.returnSinceAdded)} since add`
                          : 'Baseline price pending'}
                      </div>
                    </div>
                  </div>
                )}
              </section>
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 2: ALGORITHMIC STRATEGY BACKTEST ANALYTICS                             */}
          {/* ========================================================================= */}
          {activeTab === 'backtest' && backtest && (
            <div className="space-y-6 sm:space-y-8 animate-fade-in">
              {/* Educational Simulation Banner */}
              <div className="flex items-start gap-3 p-4 rounded-2xl bg-accent-teal/10 border border-accent-teal/20 text-tx-primary text-xs">
                <HelpCircle className="w-5 h-5 text-accent-teal shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="font-semibold text-accent-teal text-sm">
                    Simulated Quantitative Backtest Results
                  </div>
                  <p className="text-tx-secondary leading-relaxed">
                    Metrics displayed below represent algorithmic backtesting across historical OHLCV data using the <strong>{backtest.strategy_name}</strong> strategy. Past performance and simulated returns are educational in nature and do not represent guaranteed future trading performance.
                  </p>
                </div>
              </div>

              {/* Strategy Identification Details Card */}
              <div className="bg-surface rounded-2xl border border-border-primary p-5 sm:p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="text-xs uppercase font-semibold text-tx-muted">Active Strategy</div>
                  <div className="text-xl sm:text-2xl font-heading font-bold text-tx-primary">
                    {backtest.strategy_name}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-tx-secondary flex-wrap pt-1">
                    <span>Period: <strong className="text-tx-primary">{backtest.period}</strong></span>
                    {backtest.start_date && backtest.end_date && (
                      <span>· Dates: <strong className="text-tx-primary">{backtest.start_date} → {backtest.end_date}</strong></span>
                    )}
                    {backtest.run_id && (
                      <span>· Run ID: <strong className="font-mono text-tx-primary">{backtest.run_id}</strong></span>
                    )}
                  </div>
                </div>

                {/* Sample Universe Symbols */}
                {backtest.symbols && backtest.symbols.length > 0 && (
                  <div className="flex flex-col md:items-end gap-1.5">
                    <span className="text-[11px] text-tx-muted font-semibold uppercase">Covered Universe Sample</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {backtest.symbols.slice(0, 5).map((sym) => (
                        <span
                          key={sym}
                          className="px-2 py-0.5 rounded-md bg-surface-secondary border border-border-primary text-xs font-mono font-medium text-tx-primary"
                        >
                          {sym}
                        </span>
                      ))}
                      {backtest.symbols.length > 5 && (
                        <span className="text-xs text-tx-muted font-mono">
                          +{backtest.symbols.length - 5} more
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Detailed Performance Metric Cards */}
              <section aria-labelledby="backtest-metrics-heading">
                <h3 id="backtest-metrics-heading" className="sr-only">Backtest Performance Metrics</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                  <MetricCard
                    title="Strategy Win Rate"
                    value={backtest.win_rate != null ? `${backtest.win_rate.toFixed(1)}%` : '—'}
                    subtitle={`${backtest.winning_trades} Wins / ${backtest.losing_trades} Losses`}
                    isPositive={backtest.win_rate != null ? backtest.win_rate >= 50 : null}
                    extra={
                      <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                        <Award className="w-5 h-5" />
                      </div>
                    }
                  />

                  <MetricCard
                    title="Total Return (CAGR)"
                    value={backtest.total_return_pct != null ? formatPercent(backtest.total_return_pct) : '—'}
                    subtitle={backtest.total_pl != null ? `P&L: ${formatCurrency(backtest.total_pl, { decimals: 0 })}` : 'Net simulation return'}
                    isPositive={backtest.total_return_pct != null ? backtest.total_return_pct >= 0 : null}
                    extra={
                      <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                        <TrendingUp className="w-5 h-5" />
                      </div>
                    }
                  />

                  <MetricCard
                    title="Profit Factor"
                    value={backtest.profit_factor != null ? formatRatio(backtest.profit_factor, { format: 'multiplier' }) : '—'}
                    subtitle="Gross Profit / Gross Loss"
                    isPositive={backtest.profit_factor != null ? backtest.profit_factor >= 1.5 : null}
                    extra={
                      <div className="w-10 h-10 rounded-xl bg-accent-teal/10 text-accent-teal flex items-center justify-center">
                        <Activity className="w-5 h-5" />
                      </div>
                    }
                  />

                  <MetricCard
                    title="Max Drawdown"
                    value={backtest.max_drawdown_pct != null ? `-${backtest.max_drawdown_pct.toFixed(1)}%` : '—'}
                    subtitle="Peak-to-trough decline"
                    isPositive={backtest.max_drawdown_pct != null ? false : null}
                    extra={
                      <div className="w-10 h-10 rounded-xl bg-accent-red/10 text-accent-red flex items-center justify-center">
                        <TrendingDown className="w-5 h-5" />
                      </div>
                    }
                  />
                </div>
              </section>

              {/* Trade Execution Distribution Bar */}
              <div className="bg-surface rounded-2xl border border-border-primary p-5 sm:p-6 shadow-sm space-y-4">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold uppercase tracking-wider text-tx-secondary">
                    Trade Distribution & Execution Breakdown
                  </span>
                  <span className="text-tx-muted font-mono">
                    Total Executed: {backtest.total_trades} Trades
                  </span>
                </div>

                {/* Multi-segment distribution bar */}
                <div className="h-3 w-full bg-surface-secondary rounded-full overflow-hidden flex">
                  {backtest.closed_trades > 0 && (
                    <>
                      <div
                        className="bg-accent-green h-full transition-all duration-300"
                        style={{ width: `${(backtest.winning_trades / backtest.total_trades) * 100}%` }}
                        title={`Winning Trades: ${backtest.winning_trades}`}
                      />
                      <div
                        className="bg-accent-red h-full transition-all duration-300"
                        style={{ width: `${(backtest.losing_trades / backtest.total_trades) * 100}%` }}
                        title={`Losing Trades: ${backtest.losing_trades}`}
                      />
                    </>
                  )}
                  {backtest.open_trades > 0 && (
                    <div
                      className="bg-accent-teal h-full transition-all duration-300"
                      style={{ width: `${(backtest.open_trades / backtest.total_trades) * 100}%` }}
                      title={`Open Trades: ${backtest.open_trades}`}
                    />
                  )}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-accent-green shrink-0" />
                    <span>Winning: <strong className="text-tx-primary font-mono">{backtest.winning_trades}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-accent-red shrink-0" />
                    <span>Losing: <strong className="text-tx-primary font-mono">{backtest.losing_trades}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-accent-teal shrink-0" />
                    <span>Open Positions: <strong className="text-tx-primary font-mono">{backtest.open_trades}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-border-primary shrink-0" />
                    <span>Sharpe Ratio: <strong className="text-tx-primary font-mono">{backtest.sharpe_ratio ?? '—'}</strong></span>
                  </div>
                </div>

                {/* Trade Return Averages */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-border-primary/60 text-xs">
                  <div className="p-3 rounded-xl bg-surface-secondary/40 border border-border-primary/40">
                    <span className="text-tx-muted text-[11px] uppercase font-semibold">Average Trade Return</span>
                    <div className="text-base font-bold font-mono text-tx-primary mt-0.5">
                      {backtest.avg_trade_return_pct != null ? formatPercent(backtest.avg_trade_return_pct) : '—'}
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-secondary/40 border border-border-primary/40">
                    <span className="text-tx-muted text-[11px] uppercase font-semibold">Average Winning Trade</span>
                    <div className="text-base font-bold font-mono text-accent-green mt-0.5">
                      {backtest.avg_winning_trade_pct != null ? formatPercent(backtest.avg_winning_trade_pct) : '—'}
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-secondary/40 border border-border-primary/40">
                    <span className="text-tx-muted text-[11px] uppercase font-semibold">Average Losing Trade</span>
                    <div className="text-base font-bold font-mono text-accent-red mt-0.5">
                      {backtest.avg_losing_trade_pct != null ? formatPercent(backtest.avg_losing_trade_pct) : '—'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Interactive Equity Curve & Drawdown Visualizer */}
              <EquityCurveChart
                series={backtest.equity_curve}
                title={`${backtest.strategy_name} — Equity Curve`}
              />

              {/* Monthly Returns Breakdown Table */}
              {backtest.hasMonthlyReturns && backtest.monthly_returns.length > 0 && (
                <div className="bg-surface rounded-2xl border border-border-primary shadow-sm overflow-hidden">
                  <div className="p-4 sm:p-5 border-b border-border-primary flex justify-between items-center">
                    <div>
                      <h4 className="font-heading font-bold text-base text-tx-primary">
                        Monthly Return Distribution
                      </h4>
                      <p className="text-xs text-tx-secondary mt-0.5">
                        Performance breakdown by month across closed swing positions
                      </p>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm border-collapse">
                      <thead>
                        <tr className="bg-surface-secondary/60 text-tx-secondary font-semibold text-xs tracking-wider border-b border-border-primary">
                          <th scope="col" className="px-5 py-3.5">MONTH</th>
                          <th scope="col" className="px-4 py-3.5">RETURN (%)</th>
                          <th scope="col" className="px-4 py-3.5">TRADES</th>
                          <th scope="col" className="px-4 py-3.5">PERFORMANCE BAR</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-primary">
                        {backtest.monthly_returns.map((m, idx) => {
                          const isPos = m.return_pct >= 0;
                          const barWidth = Math.min(Math.abs(m.return_pct) * 8, 100);

                          return (
                            <tr key={m.month || idx} className="hover:bg-surface-secondary/40 transition-colors">
                              <td className="px-5 py-3 font-medium text-tx-primary font-mono text-xs">
                                {m.month}
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap">
                                <span className={`inline-flex items-center gap-0.5 font-mono text-xs font-semibold px-2 py-0.5 rounded ${
                                  isPos ? 'text-accent-green bg-accent-green/10' : 'text-accent-red bg-accent-red/10'
                                }`}>
                                  {isPos ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                  {formatPercent(m.return_pct)}
                                </span>
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap text-xs font-mono text-tx-secondary">
                                {m.trades} trades {m.win_count != null ? `(${m.win_count} wins)` : ''}
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap">
                                <div className="w-32 h-2 bg-surface-secondary rounded-full overflow-hidden">
                                  <div
                                    className={`h-full ${isPos ? 'bg-accent-green' : 'bg-accent-red'}`}
                                    style={{ width: `${barWidth}%` }}
                                  />
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 3: WATCHLIST FORWARD TRACKING (Phase 17 tracking integration)           */}
          {/* ========================================================================= */}
          {activeTab === 'watchlist' && (
            <div className="space-y-6 sm:space-y-8 animate-fade-in">
              {/* Educational Non-Realized Callout */}
              <div className="flex items-start gap-3 p-4 rounded-2xl bg-amber-400/10 border border-amber-400/20 text-tx-primary text-xs">
                <Star className="w-5 h-5 fill-amber-400 text-amber-500 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="font-semibold text-amber-500 text-sm">
                    Hypothetical Forward Watchlist Tracking
                  </div>
                  <p className="text-tx-secondary leading-relaxed">
                    Watchlist performance calculates price changes from the moment you saved an equity to your watchlist using its captured reference price. <strong>This does not represent an actual funded brokerage portfolio or realized P&L.</strong>
                  </p>
                </div>
              </div>

              {/* Watchlist Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                <MetricCard
                  title="Tracked Stocks"
                  value={watchlistMetrics.totalTracked.toString()}
                  subtitle={`${watchlistMetrics.pricedCount} with baseline price`}
                  extra={
                    <div className="w-10 h-10 rounded-xl bg-amber-400/10 text-amber-500 flex items-center justify-center">
                      <Star className="w-5 h-5 fill-amber-400 text-amber-500" />
                    </div>
                  }
                />

                <MetricCard
                  title="Avg Return Since Added"
                  value={
                    watchlistMetrics.avgReturnSinceAdded != null
                      ? formatPercent(watchlistMetrics.avgReturnSinceAdded)
                      : '—'
                  }
                  subtitle={watchlistMetrics.pricedCount > 0 ? `Across ${watchlistMetrics.pricedCount} priced stocks` : 'Baseline price pending'}
                  isPositive={
                    watchlistMetrics.avgReturnSinceAdded != null
                      ? watchlistMetrics.avgReturnSinceAdded >= 0
                      : null
                  }
                  extra={
                    <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                      <TrendingUp className="w-5 h-5" />
                    </div>
                  }
                />

                <MetricCard
                  title="Forward Gainers"
                  value={watchlistMetrics.gainersCount.toString()}
                  subtitle="Positive return since add date"
                  isPositive={true}
                  extra={
                    <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                  }
                />

                <MetricCard
                  title="Forward Decliners"
                  value={watchlistMetrics.declinersCount.toString()}
                  subtitle="Negative return since add date"
                  isPositive={watchlistMetrics.declinersCount === 0 ? null : false}
                  extra={
                    <div className="w-10 h-10 rounded-xl bg-accent-red/10 text-accent-red flex items-center justify-center">
                      <XCircle className="w-5 h-5" />
                    </div>
                  }
                />
              </div>

              {/* Watchlist Table Controls & Search */}
              <div className="bg-surface rounded-2xl border border-border-primary p-4 sm:p-5 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="relative flex-1 max-w-md">
                    <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-tx-muted" />
                    <input
                      type="text"
                      value={watchlistSearch}
                      onChange={(e) => setWatchlistSearch(e.target.value)}
                      placeholder="Search tracked stocks by symbol or company name..."
                      className="w-full pl-9 pr-4 py-2 bg-surface-secondary border border-border-primary rounded-xl text-tx-primary text-xs sm:text-sm placeholder:text-tx-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
                    />
                  </div>

                  {/* Filter Pills */}
                  <div className="inline-flex items-center p-1 bg-surface-secondary border border-border-primary rounded-xl text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => setWatchlistFilter('ALL')}
                      className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                        watchlistFilter === 'ALL' ? 'bg-surface text-tx-primary shadow-xs' : 'text-tx-secondary hover:text-tx-primary'
                      }`}
                    >
                      All ({watchlistMetrics.totalTracked})
                    </button>
                    <button
                      type="button"
                      onClick={() => setWatchlistFilter('GAINERS')}
                      className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                        watchlistFilter === 'GAINERS' ? 'bg-accent-green/15 text-accent-green shadow-xs' : 'text-tx-secondary hover:text-tx-primary'
                      }`}
                    >
                      Gainers ({watchlistMetrics.gainersCount})
                    </button>
                    <button
                      type="button"
                      onClick={() => setWatchlistFilter('DECLINERS')}
                      className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                        watchlistFilter === 'DECLINERS' ? 'bg-accent-red/15 text-accent-red shadow-xs' : 'text-tx-secondary hover:text-tx-primary'
                      }`}
                    >
                      Decliners ({watchlistMetrics.declinersCount})
                    </button>
                  </div>
                </div>

                {/* Watchlist Table */}
                {watchlist.length === 0 ? (
                  <div className="py-12 text-center text-xs text-tx-secondary space-y-3">
                    <Star className="w-8 h-8 text-amber-500 fill-amber-400/20 mx-auto" />
                    <p className="max-w-md mx-auto">
                      You haven't saved any stocks to your watchlist yet. Add stocks from the Stock Explorer to track their performance over time.
                    </p>
                    <Link
                      to="/stocks"
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-accent-green text-surface text-xs font-semibold hover:bg-accent-green/90 transition-colors shadow-xs"
                    >
                      <span>Explore Stocks Universe</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                ) : filteredWatchlistStocks.length === 0 ? (
                  <div className="py-8 text-center text-xs text-tx-muted">
                    No tracked stocks match your search or filter.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm border-collapse">
                      <thead>
                        <tr className="bg-surface-secondary/60 text-tx-secondary font-semibold text-xs tracking-wider border-b border-border-primary">
                          <th scope="col" className="px-4 py-3">STOCK</th>
                          <th scope="col" className="px-4 py-3">ADDED DATE</th>
                          <th scope="col" className="px-4 py-3">ADDED BASELINE</th>
                          <th scope="col" className="px-4 py-3">LATEST PRICE</th>
                          <th scope="col" className="px-4 py-3">DAILY CHANGE</th>
                          <th scope="col" className="px-4 py-3">RETURN SINCE ADDED</th>
                          <th scope="col" className="px-4 py-3 text-right">ACTION</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-primary">
                        {filteredWatchlistStocks.map((stock) => {
                          const hasPerf = stock.returnSinceAdded != null;
                          const isPos = hasPerf ? stock.returnSinceAdded >= 0 : null;

                          return (
                            <tr key={stock.symbol} className="hover:bg-surface-secondary/40 transition-colors">
                              <td className="px-4 py-3">
                                <Link
                                  to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                                  className="font-bold text-sm text-tx-primary hover:text-accent-green font-mono inline-flex items-center gap-1"
                                >
                                  {stock.symbol}
                                  <ArrowUpRight className="w-3.5 h-3.5 opacity-50" />
                                </Link>
                                <div className="text-xs text-tx-secondary truncate max-w-[180px]">
                                  {stock.company_name}
                                </div>
                              </td>

                              <td className="px-4 py-3 whitespace-nowrap text-xs text-tx-secondary font-mono">
                                {stock.addedAt ? stock.addedAt.slice(0, 10) : '—'}
                              </td>

                              <td className="px-4 py-3 whitespace-nowrap text-xs text-tx-primary font-mono font-medium">
                                {stock.addedPrice ? formatCurrency(stock.addedPrice) : '—'}
                              </td>

                              <td className="px-4 py-3 whitespace-nowrap text-xs text-tx-primary font-mono font-semibold">
                                {stock.current_price ? formatCurrency(stock.current_price) : '—'}
                              </td>

                              <td className="px-4 py-3 whitespace-nowrap">
                                {stock.daily_change_percent != null ? (
                                  <span className={`inline-flex items-center gap-0.5 text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                                    Number(stock.daily_change_percent) >= 0 ? 'text-accent-green bg-accent-green/10' : 'text-accent-red bg-accent-red/10'
                                  }`}>
                                    {Number(stock.daily_change_percent) >= 0 ? '+' : ''}
                                    {Number(stock.daily_change_percent).toFixed(2)}%
                                  </span>
                                ) : (
                                  <span className="text-xs text-tx-muted">—</span>
                                )}
                              </td>

                              <td className="px-4 py-3 whitespace-nowrap">
                                {hasPerf ? (
                                  <div className="flex flex-col">
                                    <span className={`inline-flex items-center gap-0.5 text-xs font-mono font-semibold px-2 py-0.5 rounded w-fit ${
                                      isPos ? 'text-accent-green bg-accent-green/10' : 'text-accent-red bg-accent-red/10'
                                    }`}>
                                      {isPos ? '+' : ''}{stock.returnSinceAdded.toFixed(2)}%
                                    </span>
                                    {stock.priceDifference != null && (
                                      <span className="text-[10px] font-mono text-tx-muted mt-0.5">
                                        {stock.priceDifference >= 0 ? '+' : ''}{formatCurrency(stock.priceDifference)}
                                      </span>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-xs text-tx-muted font-mono">Unset</span>
                                )}
                              </td>

                              <td className="px-4 py-3 whitespace-nowrap text-right">
                                <Link
                                  to={`/stocks/${encodeURIComponent(stock.symbol)}`}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-secondary border border-border-primary hover:bg-surface-secondary/80 hover:text-accent-green text-xs font-medium text-tx-primary transition-colors"
                                >
                                  <span>Analyze</span>
                                  <ArrowUpRight className="w-3.5 h-3.5" />
                                </Link>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
