import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Filter,
  ArrowUpDown,
  ArrowUpRight,
  TrendingUp,
  TrendingDown,
  Eye,
  RefreshCw,
  SlidersHorizontal,
  X,
  LayoutGrid,
  List,
  ShieldAlert,
  Target,
  Sparkles,
  BarChart3
} from 'lucide-react';
import { getOpportunities } from '../services/api';
import MetricCard from '../components/MetricCard';
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents';

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
        <div className={`h-full ${color} transition-all duration-300`} style={{ width: `${percentage}%` }}></div>
      </div>
      <span className="text-xs font-semibold text-tx-primary font-mono">{numericScore.toFixed(1)}</span>
    </div>
  );
};

const DirectionBadge = ({ recommendation, direction }) => {
  const norm = (recommendation || direction || '').toUpperCase();

  if (norm === 'BUY' || norm === 'BULLISH') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded-md bg-accent-green/10 text-accent-green border border-accent-green/20">
        <TrendingUp className="w-3 h-3 shrink-0" />
        Bullish
      </span>
    );
  }
  if (norm === 'SELL' || norm === 'BEARISH') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded-md bg-accent-red/10 text-accent-red border border-accent-red/20">
        <TrendingDown className="w-3 h-3 shrink-0" />
        Bearish
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

const Opportunities = () => {
  const [oppsState, setOppsState] = useState({ data: [], loading: true, error: null });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(() => new Date());

  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState('');
  const [directionFilter, setDirectionFilter] = useState('ALL');
  const [sectorFilter, setSectorFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('score-desc');
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'cards'

  const isMountedRef = useRef(true);

  const fetchOpps = useCallback(async (isInitial = false) => {
    if (!isInitial) {
      setOppsState(prev => ({ ...prev, loading: true, error: null }));
    }
    try {
      const res = await getOpportunities();
      if (isMountedRef.current) {
        const list = Array.isArray(res) ? res : res?.opportunities || [];
        setOppsState({ data: list, loading: false, error: null });
        setLastRefreshed(new Date());
      }
    } catch (err) {
      if (isMountedRef.current) {
        setOppsState({
          data: [],
          loading: false,
          error: err.message || 'Unable to load opportunities from the intelligence engine.'
        });
      }
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await fetchOpps(false);
    } finally {
      if (isMountedRef.current) {
        setIsRefreshing(false);
      }
    }
  }, [fetchOpps]);

  useEffect(() => {
    isMountedRef.current = true;

    const init = async () => {
      await fetchOpps();
    };
    init();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchOpps]);

  const rawOpportunities = oppsState.data;

  // Distinct sectors for filter dropdown
  const uniqueSectors = useMemo(() => {
    if (!rawOpportunities) return [];
    const set = new Set();
    rawOpportunities.forEach(opp => {
      if (opp.sector) set.add(opp.sector);
    });
    return Array.from(set).sort();
  }, [rawOpportunities]);

  // Filtered & Sorted opportunities
  const filteredOpportunities = useMemo(() => {
    if (!rawOpportunities) return [];

    return rawOpportunities
      .filter(opp => {
        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          const matchSym = (opp.symbol || '').toLowerCase().includes(q);
          const matchName = (opp.company_name || '').toLowerCase().includes(q);
          const matchSec = (opp.sector || '').toLowerCase().includes(q);
          if (!matchSym && !matchName && !matchSec) return false;
        }

        // Direction filter
        if (directionFilter !== 'ALL') {
          const norm = (opp.recommendation || opp.direction || '').toUpperCase();
          if (directionFilter === 'BULLISH' && norm !== 'BUY' && norm !== 'BULLISH') return false;
          if (directionFilter === 'BEARISH' && norm !== 'SELL' && norm !== 'BEARISH') return false;
          if (directionFilter === 'WATCH' && norm !== 'WATCH' && norm !== 'NEUTRAL') return false;
        }

        // Sector filter
        if (sectorFilter !== 'ALL') {
          if (opp.sector !== sectorFilter) return false;
        }

        return true;
      })
      .sort((a, b) => {
        switch (sortBy) {
          case 'score-desc':
            return (b.opportunity_score ?? 0) - (a.opportunity_score ?? 0);
          case 'score-asc':
            return (a.opportunity_score ?? 0) - (b.opportunity_score ?? 0);
          case 'rr-desc':
            return (b.risk_reward ?? 0) - (a.risk_reward ?? 0);
          case 'price-desc':
            return (b.current_price ?? 0) - (a.current_price ?? 0);
          case 'price-asc':
            return (a.current_price ?? 0) - (b.current_price ?? 0);
          case 'change-desc':
            return (b.price_change_percent ?? 0) - (a.price_change_percent ?? 0);
          case 'symbol-asc':
            return (a.symbol || '').localeCompare(b.symbol || '');
          default:
            return 0;
        }
      });
  }, [rawOpportunities, searchQuery, directionFilter, sectorFilter, sortBy]);

  // Summary Metrics calculations
  const summaryMetrics = useMemo(() => {
    if (!rawOpportunities || rawOpportunities.length === 0) {
      return { total: 0, bullish: 0, bearish: 0, watch: 0, avgScore: null, avgRR: null };
    }

    let bullish = 0;
    let bearish = 0;
    let watch = 0;
    let scoreSum = 0;
    let scoreCount = 0;
    let rrSum = 0;
    let rrCount = 0;

    rawOpportunities.forEach(opp => {
      const rec = (opp.recommendation || opp.direction || '').toUpperCase();
      if (rec === 'BUY' || rec === 'BULLISH') bullish++;
      else if (rec === 'SELL' || rec === 'BEARISH') bearish++;
      else watch++;

      if (opp.opportunity_score != null && !isNaN(opp.opportunity_score)) {
        scoreSum += Number(opp.opportunity_score);
        scoreCount++;
      }
      if (opp.risk_reward != null && !isNaN(opp.risk_reward)) {
        rrSum += Number(opp.risk_reward);
        rrCount++;
      }
    });

    return {
      total: rawOpportunities.length,
      bullish,
      bearish,
      watch,
      avgScore: scoreCount > 0 ? (scoreSum / scoreCount).toFixed(1) : null,
      avgRR: rrCount > 0 ? (rrSum / rrCount).toFixed(1) : null
    };
  }, [rawOpportunities]);

  const hasActiveFilters = searchQuery !== '' || directionFilter !== 'ALL' || sectorFilter !== 'ALL';

  const resetFilters = () => {
    setSearchQuery('');
    setDirectionFilter('ALL');
    setSectorFilter('ALL');
    setSortBy('score-desc');
  };

  const formatCurrency = (val) => {
    if (val == null || isNaN(val)) return '—';
    return `₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* 1. OPPORTUNITIES HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border-primary/50">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-heading font-bold text-tx-primary tracking-tight">
              Opportunities Explorer
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
            {!oppsState.loading && (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-surface-secondary text-tx-secondary border border-border-primary font-mono">
                {rawOpportunities.length} Setups
              </span>
            )}
          </div>
          <p className="text-tx-secondary text-xs sm:text-sm mt-1">
            Quantitative multi-factor swing opportunities for Indian equities · 3–8 week horizon
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right hidden sm:block">
            <div className="text-[11px] text-tx-secondary">Last scanned</div>
            <div className="text-xs font-mono font-medium text-tx-primary">
              {lastRefreshed ? lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
            </div>
          </div>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing || oppsState.loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface border border-border-primary hover:bg-surface-secondary text-tx-primary text-xs sm:text-sm font-medium transition-colors shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green disabled:opacity-50"
            title="Rescan universe for swing setups"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-accent-green ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Scanning...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* 2. SUMMARY METRICS */}
      <section aria-labelledby="summary-metrics-heading">
        <h2 id="summary-metrics-heading" className="sr-only">Summary Metrics</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <MetricCard
            title="Total Opportunities"
            value={oppsState.loading ? '—' : summaryMetrics.total.toString()}
            subtitle="Scanned universe"
            loading={oppsState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-teal/10 text-accent-teal flex items-center justify-center">
                <Sparkles className="w-5 h-5" />
              </div>
            }
          />
          <MetricCard
            title="Bullish Setups"
            value={oppsState.loading ? '—' : summaryMetrics.bullish.toString()}
            subtitle={summaryMetrics.total > 0 ? `${((summaryMetrics.bullish / summaryMetrics.total) * 100).toFixed(0)}% of universe` : '0%'}
            isPositive={true}
            loading={oppsState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                <TrendingUp className="w-5 h-5" />
              </div>
            }
          />
          <MetricCard
            title="Watch / Bearish"
            value={oppsState.loading ? '—' : (summaryMetrics.watch + summaryMetrics.bearish).toString()}
            subtitle={`${summaryMetrics.watch} Watch · ${summaryMetrics.bearish} Bearish`}
            isPositive={summaryMetrics.bearish === 0 ? null : false}
            loading={oppsState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-surface-secondary text-tx-secondary flex items-center justify-center">
                <Eye className="w-5 h-5" />
              </div>
            }
          />
          <MetricCard
            title="Average Setup Score"
            value={oppsState.loading ? '—' : (summaryMetrics.avgScore ? `${summaryMetrics.avgScore}` : '—')}
            subtitle={summaryMetrics.avgRR ? `Avg R/R: ${summaryMetrics.avgRR}x` : 'Composite score'}
            isPositive={summaryMetrics.avgScore ? Number(summaryMetrics.avgScore) >= 70 : null}
            loading={oppsState.loading}
            extra={
              <div className="w-10 h-10 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center">
                <BarChart3 className="w-5 h-5" />
              </div>
            }
          />
        </div>
      </section>

      {/* 3. SEARCH AND FILTERS */}
      <section className="bg-surface rounded-2xl border border-border-primary shadow-sm p-4 sm:p-5 transition-colors space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-lg">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-tx-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search symbol, company, or sector..."
              className="w-full pl-9 pr-9 py-2 bg-surface-secondary border border-border-primary rounded-xl text-tx-primary text-xs sm:text-sm placeholder:text-tx-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-tx-muted hover:text-tx-primary p-0.5 rounded"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Filter Controls Row */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs sm:text-sm">
            {/* Direction Filter */}
            <div className="flex items-center gap-1.5 bg-surface-secondary border border-border-primary rounded-xl px-2.5 py-1.5">
              <Filter className="w-3.5 h-3.5 text-tx-muted shrink-0" />
              <label htmlFor="direction-select" className="sr-only">Filter by Direction</label>
              <select
                id="direction-select"
                value={directionFilter}
                onChange={(e) => setDirectionFilter(e.target.value)}
                className="bg-transparent text-tx-primary text-xs font-medium focus:outline-none cursor-pointer"
              >
                <option value="ALL">All Directions</option>
                <option value="BULLISH">Bullish (Buy)</option>
                <option value="WATCH">Watch / Neutral</option>
                <option value="BEARISH">Bearish (Sell)</option>
              </select>
            </div>

            {/* Sector Filter */}
            <div className="flex items-center gap-1.5 bg-surface-secondary border border-border-primary rounded-xl px-2.5 py-1.5">
              <label htmlFor="sector-select" className="sr-only">Filter by Sector</label>
              <select
                id="sector-select"
                value={sectorFilter}
                onChange={(e) => setSectorFilter(e.target.value)}
                className="bg-transparent text-tx-primary text-xs font-medium focus:outline-none cursor-pointer max-w-[150px] sm:max-w-none truncate"
              >
                <option value="ALL">All Sectors</option>
                {uniqueSectors.map(sec => (
                  <option key={sec} value={sec}>{sec}</option>
                ))}
              </select>
            </div>

            {/* Sort By */}
            <div className="flex items-center gap-1.5 bg-surface-secondary border border-border-primary rounded-xl px-2.5 py-1.5">
              <ArrowUpDown className="w-3.5 h-3.5 text-tx-muted shrink-0" />
              <label htmlFor="sort-select" className="sr-only">Sort opportunities</label>
              <select
                id="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-transparent text-tx-primary text-xs font-medium focus:outline-none cursor-pointer"
              >
                <option value="score-desc">Score: High to Low</option>
                <option value="score-asc">Score: Low to High</option>
                <option value="rr-desc">Risk/Reward: Highest</option>
                <option value="price-desc">Price: High to Low</option>
                <option value="price-asc">Price: Low to High</option>
                <option value="change-desc">Change %: Highest</option>
                <option value="symbol-asc">Symbol: A to Z</option>
              </select>
            </div>

            {/* View Mode Toggle (Desktop & Tablet) */}
            <div className="hidden sm:flex items-center bg-surface-secondary border border-border-primary rounded-xl p-1">
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`p-1 rounded-lg transition-colors ${viewMode === 'table' ? 'bg-surface text-tx-primary shadow-xs font-semibold' : 'text-tx-muted hover:text-tx-primary'}`}
                title="Table View"
                aria-label="Table View"
              >
                <List className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                className={`p-1 rounded-lg transition-colors ${viewMode === 'cards' ? 'bg-surface text-tx-primary shadow-xs font-semibold' : 'text-tx-muted hover:text-tx-primary'}`}
                title="Card View"
                aria-label="Card View"
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
            </div>

            {/* Clear Filters Button */}
            {hasActiveFilters && (
              <button
                type="button"
                onClick={resetFilters}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-medium text-accent-red hover:bg-accent-red/10 border border-accent-red/20 transition-colors"
                title="Reset all active filters"
              >
                <X className="w-3 h-3" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Filter status label */}
        <div className="flex items-center justify-between text-xs text-tx-secondary pt-2 border-t border-border-primary/40">
          <span>
            Showing <strong className="text-tx-primary font-mono">{filteredOpportunities.length}</strong> of{' '}
            <strong className="text-tx-primary font-mono">{rawOpportunities.length}</strong> opportunities
          </span>
          {hasActiveFilters && (
            <span className="text-accent-green font-medium">
              Filtered results active
            </span>
          )}
        </div>
      </section>

      {/* 4. OPPORTUNITIES CONTENT AREA */}
      <section aria-label="Opportunities list">
        {oppsState.loading ? (
          <div className="bg-surface rounded-2xl border border-border-primary p-12 shadow-sm">
            <LoadingState message="Scanning universe for swing opportunities..." />
          </div>
        ) : oppsState.error ? (
          <div className="bg-surface rounded-2xl border border-border-primary p-8 shadow-sm">
            <ErrorState
              title="Could not load swing opportunities"
              message={oppsState.error}
              onRetry={fetchOpps}
            />
          </div>
        ) : rawOpportunities.length === 0 ? (
          <div className="bg-surface rounded-2xl border border-border-primary p-12 shadow-sm">
            <EmptyState message="No qualifying swing opportunities found in the current universe scan." />
          </div>
        ) : filteredOpportunities.length === 0 ? (
          <div className="bg-surface rounded-2xl border border-border-primary p-12 text-center shadow-sm space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full bg-surface-secondary text-tx-muted flex items-center justify-center">
              <SlidersHorizontal className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-tx-primary mb-1">No matching opportunities</h3>
              <p className="text-xs text-tx-secondary max-w-md mx-auto">
                No setups match your current filters. Try searching with different keywords or clearing your active filters.
              </p>
            </div>
            <button
              type="button"
              onClick={resetFilters}
              className="px-4 py-2 bg-surface-secondary border border-border-primary rounded-xl text-xs font-semibold text-tx-primary hover:bg-surface-secondary/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green transition-colors"
            >
              Clear All Filters
            </button>
          </div>
        ) : (
          <>
            {/* TABLE VIEW (Default on desktop or when toggled) */}
            <div className={viewMode === 'table' ? 'block' : 'hidden sm:hidden'}>
              <div className="bg-surface rounded-2xl border border-border-primary shadow-sm overflow-hidden transition-colors">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm border-collapse">
                    <thead>
                      <tr className="bg-surface-secondary/60 text-tx-secondary font-semibold text-xs tracking-wider border-b border-border-primary">
                        <th scope="col" className="px-5 py-3.5">STOCK</th>
                        <th scope="col" className="px-4 py-3.5">DIRECTION</th>
                        <th scope="col" className="px-4 py-3.5">OPP SCORE</th>
                        <th scope="col" className="px-4 py-3.5">SETUP</th>
                        <th scope="col" className="px-4 py-3.5">PRICE</th>
                        <th scope="col" className="px-4 py-3.5">ENTRY RANGE</th>
                        <th scope="col" className="px-4 py-3.5">STOP LOSS</th>
                        <th scope="col" className="px-4 py-3.5">TARGET</th>
                        <th scope="col" className="px-4 py-3.5">R/R</th>
                        <th scope="col" className="px-4 py-3.5 text-right">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-primary">
                      {filteredOpportunities.map((opp, idx) => {
                        const priceChange = opp.price_change_percent;
                        const hasChange = priceChange != null && !isNaN(priceChange);
                        const isPosChange = hasChange ? Number(priceChange) >= 0 : null;

                        const entryText = opp.entry_zone_low && opp.entry_zone_high
                          ? `₹${Number(opp.entry_zone_low).toLocaleString('en-IN')} – ₹${Number(opp.entry_zone_high).toLocaleString('en-IN')}`
                          : opp.entry_price != null
                          ? formatCurrency(opp.entry_price)
                          : '—';

                        return (
                          <tr
                            key={opp.symbol || idx}
                            className="hover:bg-surface-secondary/50 transition-colors group"
                          >
                            {/* Stock Symbol & Company */}
                            <td className="px-5 py-4">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xs font-mono font-medium text-tx-muted w-5 shrink-0">
                                  {opp.rank ? `#${opp.rank}` : `${idx + 1}`}
                                </span>
                                <div>
                                  <Link
                                    to={`/stocks/${encodeURIComponent(opp.symbol)}`}
                                    className="font-heading font-bold text-base text-tx-primary hover:text-accent-green inline-flex items-center gap-1 transition-colors"
                                  >
                                    {opp.symbol}
                                    <ArrowUpRight className="w-3.5 h-3.5 opacity-50 group-hover:opacity-100 transition-opacity" />
                                  </Link>
                                  <div className="text-xs text-tx-secondary truncate max-w-[170px]" title={opp.company_name}>
                                    {opp.company_name || '—'}
                                  </div>
                                  {opp.sector && (
                                    <span className="inline-block mt-0.5 text-[10px] text-tx-muted font-medium px-1.5 py-0.2 bg-surface-secondary rounded">
                                      {opp.sector}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </td>

                            {/* Direction */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <DirectionBadge recommendation={opp.recommendation} direction={opp.direction} />
                            </td>

                            {/* Composite Opportunity Score */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <ScoreBadge score={opp.opportunity_score} />
                            </td>

                            {/* Technical Setup Score */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <ScoreBadge score={opp.technical_score} />
                            </td>

                            {/* Price & Change */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <div className="font-mono font-semibold text-tx-primary text-sm">
                                {formatCurrency(opp.current_price)}
                              </div>
                              {hasChange && (
                                <span className={`text-xs font-mono font-medium ${isPosChange ? 'text-accent-green' : 'text-accent-red'}`}>
                                  {isPosChange ? '+' : ''}{Number(priceChange).toFixed(2)}%
                                </span>
                              )}
                            </td>

                            {/* Entry Zone */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <span className="text-xs font-mono font-medium text-tx-secondary">
                                {entryText}
                              </span>
                            </td>

                            {/* Stop Loss */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <span className="text-xs font-mono font-medium text-accent-red">
                                {formatCurrency(opp.stop_loss)}
                              </span>
                            </td>

                            {/* Target */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              <span className="text-xs font-mono font-medium text-accent-green">
                                {formatCurrency(opp.target)}
                              </span>
                            </td>

                            {/* Risk / Reward */}
                            <td className="px-4 py-4 whitespace-nowrap">
                              {opp.risk_reward != null ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold bg-accent-green/10 text-accent-green">
                                  {Number(opp.risk_reward).toFixed(1)}x
                                </span>
                              ) : (
                                <span className="text-xs text-tx-secondary">—</span>
                              )}
                            </td>

                            {/* Action Button */}
                            <td className="px-4 py-4 whitespace-nowrap text-right">
                              <Link
                                to={`/stocks/${encodeURIComponent(opp.symbol)}`}
                                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-secondary border border-border-primary hover:bg-surface-secondary/80 hover:text-accent-green text-tx-primary text-xs font-medium transition-colors"
                              >
                                <span>Details</span>
                                <ArrowUpRight className="w-3.5 h-3.5" />
                              </Link>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="p-4 border-t border-border-primary bg-surface-secondary/30 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-tx-secondary">
                  <span>
                    Systematic swing setups scored across Technical, Financial, Sector & Risk metrics.
                  </span>
                  <span className="font-mono text-[11px]">
                    Universe: NIFTY 50 Indian Equities
                  </span>
                </div>
              </div>
            </div>

            {/* CARD VIEW (For mobile screens or when card view is toggled) */}
            <div className={viewMode === 'cards' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6' : 'grid sm:hidden grid-cols-1 gap-4'}>
              {filteredOpportunities.map((opp, idx) => {
                const priceChange = opp.price_change_percent;
                const hasChange = priceChange != null && !isNaN(priceChange);
                const isPosChange = hasChange ? Number(priceChange) >= 0 : null;

                const entryText = opp.entry_zone_low && opp.entry_zone_high
                  ? `₹${Number(opp.entry_zone_low).toLocaleString('en-IN')} – ₹${Number(opp.entry_zone_high).toLocaleString('en-IN')}`
                  : opp.entry_price != null
                  ? formatCurrency(opp.entry_price)
                  : '—';

                return (
                  <div
                    key={opp.symbol || idx}
                    className="bg-surface rounded-2xl border border-border-primary shadow-sm p-5 hover:border-border-primary/80 transition-all flex flex-col justify-between space-y-4"
                  >
                    <div>
                      {/* Top Row: Rank, Symbol, Sector, Direction */}
                      <div className="flex justify-between items-start gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-semibold text-tx-muted px-1.5 py-0.5 bg-surface-secondary rounded">
                            {opp.rank ? `#${opp.rank}` : `${idx + 1}`}
                          </span>
                          <div>
                            <Link
                              to={`/stocks/${encodeURIComponent(opp.symbol)}`}
                              className="font-heading font-bold text-lg text-tx-primary hover:text-accent-green inline-flex items-center gap-1 transition-colors"
                            >
                              {opp.symbol}
                              <ArrowUpRight className="w-4 h-4 opacity-60" />
                            </Link>
                            <div className="text-xs text-tx-secondary truncate max-w-[180px]">
                              {opp.company_name || '—'}
                            </div>
                          </div>
                        </div>
                        <DirectionBadge recommendation={opp.recommendation} direction={opp.direction} />
                      </div>

                      {/* Sector badge */}
                      {opp.sector && (
                        <div className="mb-4">
                          <span className="text-[11px] text-tx-muted font-medium px-2 py-0.5 bg-surface-secondary rounded-md">
                            {opp.sector}
                          </span>
                        </div>
                      )}

                      {/* Price & Change Banner */}
                      <div className="flex justify-between items-baseline p-3 rounded-xl bg-surface-secondary/40 border border-border-primary/50 mb-4">
                        <div>
                          <span className="text-[11px] text-tx-muted uppercase tracking-wider block">Price</span>
                          <span className="font-mono font-bold text-base text-tx-primary">
                            {formatCurrency(opp.current_price)}
                          </span>
                        </div>
                        {hasChange && (
                          <div className="text-right">
                            <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${isPosChange ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'}`}>
                              {isPosChange ? '+' : ''}{Number(priceChange).toFixed(2)}%
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Scores Breakdown */}
                      <div className="space-y-2 mb-4 text-xs">
                        <div className="flex justify-between items-center">
                          <span className="text-tx-secondary">Opportunity Score</span>
                          <ScoreBadge score={opp.opportunity_score} />
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-tx-secondary">Technical Setup</span>
                          <ScoreBadge score={opp.technical_score} />
                        </div>
                      </div>

                      {/* Trade Plan Box */}
                      <div className="p-3 rounded-xl bg-surface-secondary/50 border border-border-primary/60 space-y-2 text-xs">
                        <div className="flex justify-between items-center">
                          <span className="text-tx-secondary">Entry Range:</span>
                          <span className="font-mono font-medium text-tx-primary">{entryText}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-tx-secondary flex items-center gap-1">
                            <ShieldAlert className="w-3 h-3 text-accent-red" />
                            Stop Loss:
                          </span>
                          <span className="font-mono font-medium text-accent-red">{formatCurrency(opp.stop_loss)}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-tx-secondary flex items-center gap-1">
                            <Target className="w-3 h-3 text-accent-green" />
                            Target:
                          </span>
                          <span className="font-mono font-medium text-accent-green">{formatCurrency(opp.target)}</span>
                        </div>
                        {opp.risk_reward != null && (
                          <div className="flex justify-between items-center pt-1 border-t border-border-primary/40">
                            <span className="text-tx-secondary font-medium">Risk/Reward:</span>
                            <span className="font-mono font-bold text-accent-green text-xs px-1.5 py-0.2 bg-accent-green/10 rounded">
                              {Number(opp.risk_reward).toFixed(1)}x
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Card Footer with Details Link */}
                    <div className="pt-2 border-t border-border-primary/50">
                      <Link
                        to={`/stocks/${encodeURIComponent(opp.symbol)}`}
                        className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-surface-secondary hover:bg-surface-secondary/80 hover:text-accent-green border border-border-primary text-tx-primary text-xs font-semibold transition-colors"
                      >
                        <span>Analyze Setup</span>
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
    </div>
  );
};

export default Opportunities;
