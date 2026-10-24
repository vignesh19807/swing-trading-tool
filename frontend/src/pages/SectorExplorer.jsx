import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Layers,
  Search,
  Filter,
  ArrowUpDown,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  LayoutGrid,
  List,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Building2,
  BarChart3,
  Sparkles,
  Info
} from 'lucide-react';
import { getSectors, getStocks } from '../services/api';
import MetricCard from '../components/MetricCard';
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents';
import { formatCurrency, formatPercent } from '../utils/formatters';
import {
  normalizeSectorData,
  filterSectors,
  sortSectors,
  calculateSectorSummary
} from '../utils/sectorHelpers';

const getStatusIcon = (status) => {
  if (status === 'Outperforming') return TrendingUp;
  if (status === 'Lagging') return TrendingDown;
  return Minus;
};

const SectorExplorer = () => {
  const [sectorsState, setSectorsState] = useState({ data: [], loading: true, error: null });
  const [stocksState, setStocksState] = useState({ data: [], loading: true, error: null });
  const [expandedSectors, setExpandedSectors] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL' | 'Outperforming' | 'In-line' | 'Lagging'
  const [timeframe, setTimeframe] = useState('63d'); // '21d' | '63d' | '126d'
  const [sortBy, setSortBy] = useState('performance-desc');
  const [viewMode, setViewMode] = useState('cards'); // 'cards' | 'table'
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(() => new Date());

  const isMountedRef = useRef(true);

  const loadData = useCallback(async (isInitial = false) => {
    if (!isInitial) {
      setSectorsState(prev => ({ ...prev, loading: true, error: null }));
      setStocksState(prev => ({ ...prev, loading: true, error: null }));
    }

    try {
      const [sectorsRes, stocksRes] = await Promise.allSettled([
        getSectors(),
        getStocks()
      ]);

      if (!isMountedRef.current) return;

      if (sectorsRes.status === 'fulfilled') {
        const raw = sectorsRes.value;
        const list = Array.isArray(raw)
          ? raw
          : raw?.sector_rankings || raw?.sectors || [];
        setSectorsState({ data: list, loading: false, error: null });
      } else {
        setSectorsState({
          data: [],
          loading: false,
          error: sectorsRes.reason?.message || 'Failed to load sector performance data.'
        });
      }

      if (stocksRes.status === 'fulfilled') {
        const rawStocks = stocksRes.value;
        const list = Array.isArray(rawStocks)
          ? rawStocks
          : rawStocks?.stocks || [];
        setStocksState({ data: list, loading: false, error: null });
      } else {
        setStocksState({
          data: [],
          loading: false,
          error: stocksRes.reason?.message || 'Failed to load constituent stocks.'
        });
      }

      setLastRefreshed(new Date());
    } finally {
      if (isMountedRef.current) {
        setIsRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    const init = async () => {
      await loadData(true);
    };
    init();
    return () => {
      isMountedRef.current = false;
    };
  }, [loadData]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    loadData(false);
  };

  // Toggle sector expansion to show constituent stocks
  const toggleSectorExpand = (sectorName) => {
    setExpandedSectors(prev => ({
      ...prev,
      [sectorName]: !prev[sectorName]
    }));
  };

  // Normalized sectors
  const normalizedSectors = useMemo(() => {
    return sectorsState.data.map((s, idx) => normalizeSectorData(s, idx));
  }, [sectorsState.data]);

  // Map stocks by sector for constituent lookup
  const stocksBySector = useMemo(() => {
    const map = {};
    for (const stock of stocksState.data) {
      if (stock.sector) {
        const key = stock.sector.trim().toLowerCase();
        if (!map[key]) map[key] = [];
        map[key].push(stock);
      }
    }
    return map;
  }, [stocksState.data]);

  // Filtered & Sorted sectors
  const filteredSectors = useMemo(() => {
    const filtered = filterSectors(normalizedSectors, {
      searchQuery,
      statusFilter,
      stocksBySector,
    });
    return sortSectors(filtered, sortBy, timeframe);
  }, [normalizedSectors, searchQuery, statusFilter, stocksBySector, sortBy, timeframe]);

  // Aggregate summary statistics
  const summaryStats = useMemo(() => {
    return calculateSectorSummary(normalizedSectors);
  }, [normalizedSectors]);

  // Render return value with color coding
  const renderPerformanceBadge = (val) => {
    if (val == null || isNaN(val)) {
      return <span className="text-tx-secondary font-mono text-xs">—</span>;
    }
    const isPos = val > 0;
    const isZero = val === 0;
    const colorClass = isPos
      ? 'text-accent-green'
      : isZero
      ? 'text-tx-secondary'
      : 'text-accent-red';

    return (
      <span className={`font-mono font-semibold text-xs ${colorClass}`}>
        {formatPercent(val, { showSign: true, decimals: 1 })}
      </span>
    );
  };

  return (
    <div className="p-4 sm:p-6 md:p-8 max-w-7xl mx-auto space-y-6 sm:space-y-8 animate-fade-in">
      {/* Header and Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-primary pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-lg bg-accent-teal/10 text-accent-teal" aria-hidden="true">
              <Layers className="w-5 h-5" />
            </span>
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-tx-primary tracking-tight">
              Sector Explorer
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-tx-secondary max-w-2xl">
            Relative strength analysis, momentum ranking, and constituent stock breakdown across Indian market sectors.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start md:self-auto">
          <span className="text-xs text-tx-secondary hidden sm:inline">
            Updated {lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            aria-label="Refresh sector data"
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-surface hover:bg-surface-secondary text-tx-primary rounded-xl border border-border-primary text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-accent-green' : 'text-tx-secondary'}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Overview Metrics Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <MetricCard
          title="Total Sectors"
          value={sectorsState.loading ? '...' : summaryStats.total}
          subtitle="tracked in universe"
          loading={sectorsState.loading}
          extra={<Layers className="w-5 h-5 text-accent-teal/70" />}
        />
        <MetricCard
          title="Outperforming"
          value={sectorsState.loading ? '...' : summaryStats.outperforming}
          subtitle="beating benchmark"
          isPositive={true}
          loading={sectorsState.loading}
          extra={<TrendingUp className="w-5 h-5 text-accent-green/80" />}
        />
        <MetricCard
          title="Lagging"
          value={sectorsState.loading ? '...' : summaryStats.lagging}
          subtitle="below benchmark"
          isPositive={false}
          loading={sectorsState.loading}
          extra={<TrendingDown className="w-5 h-5 text-accent-red/80" />}
        />
        <MetricCard
          title="Top Performer"
          value={sectorsState.loading ? '...' : (summaryStats.topSector ? summaryStats.topSector.name : '—')}
          subtitle={summaryStats.topSector ? `63D: ${formatPercent(summaryStats.topReturn, { showSign: true, decimals: 1 })}` : 'no data'}
          isPositive={summaryStats.topReturn > 0}
          loading={sectorsState.loading}
          extra={<Sparkles className="w-5 h-5 text-amber-400" />}
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-surface border border-border-primary rounded-2xl p-4 shadow-2xs space-y-3 sm:space-y-4">
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
          {/* Search box */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-tx-secondary" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sectors or constituent stocks..."
              aria-label="Search sectors or constituent stocks"
              className="w-full bg-surface-secondary text-tx-primary rounded-xl pl-9 pr-4 py-2 text-xs sm:text-sm border border-transparent focus:border-accent-green/30 focus:outline-none focus:ring-2 focus:ring-accent-green/20 transition-colors"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-tx-secondary hover:text-tx-primary p-0.5 text-xs"
                aria-label="Clear search query"
              >
                ✕
              </button>
            )}
          </div>

          {/* Timeframe & View Mode selectors */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Timeframe pills */}
            <div className="inline-flex p-1 bg-surface-secondary rounded-xl border border-border-primary text-xs" role="group" aria-label="Ranking Timeframe">
              {[
                { id: '21d', label: '21D (1M)' },
                { id: '63d', label: '63D (3M)' },
                { id: '126d', label: '126D (6M)' },
              ].map(t => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTimeframe(t.id)}
                  className={`px-2.5 py-1 rounded-lg font-medium transition-all cursor-pointer ${
                    timeframe === t.id
                      ? 'bg-surface text-tx-primary font-semibold shadow-2xs'
                      : 'text-tx-secondary hover:text-tx-primary'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* View Mode Toggle */}
            <div className="hidden sm:inline-flex p-1 bg-surface-secondary rounded-xl border border-border-primary text-xs" role="group" aria-label="View layout">
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                aria-label="Grid card view"
                className={`p-1.5 rounded-lg transition-all cursor-pointer ${
                  viewMode === 'cards'
                    ? 'bg-surface text-tx-primary shadow-2xs'
                    : 'text-tx-secondary hover:text-tx-primary'
                }`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                aria-label="Table list view"
                className={`p-1.5 rounded-lg transition-all cursor-pointer ${
                  viewMode === 'table'
                    ? 'bg-surface text-tx-primary shadow-2xs'
                    : 'text-tx-secondary hover:text-tx-primary'
                }`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Secondary Filter Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border-primary/60 text-xs">
          {/* Status Filter Chips */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-tx-secondary font-medium mr-1 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Performance:
            </span>
            {['ALL', 'Outperforming', 'In-line', 'Lagging'].map(st => (
              <button
                key={st}
                type="button"
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                  statusFilter === st
                    ? 'bg-accent-green text-surface font-semibold shadow-2xs'
                    : 'bg-surface-secondary hover:bg-surface-secondary/80 text-tx-secondary border border-border-primary'
                }`}
              >
                {st === 'ALL' ? 'All Sectors' : st}
              </button>
            ))}
          </div>

          {/* Sort selector */}
          <div className="flex items-center gap-2">
            <span className="text-tx-secondary flex items-center gap-1">
              <ArrowUpDown className="w-3.5 h-3.5" /> Sort:
            </span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              aria-label="Sort sectors by"
              className="bg-surface-secondary text-tx-primary border border-border-primary rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-accent-green"
            >
              <option value="performance-desc">Highest Return</option>
              <option value="performance-asc">Lowest Return</option>
              <option value="name-asc">Sector Name (A-Z)</option>
              <option value="stocks-desc">Most Constituent Stocks</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {sectorsState.loading ? (
        <LoadingState message="Fetching sector performance & rotation metrics..." />
      ) : sectorsState.error ? (
        <ErrorState
          title="Sector Intelligence Unavailable"
          message={sectorsState.error}
          onRetry={() => loadData()}
        />
      ) : filteredSectors.length === 0 ? (
        <EmptyState
          message={
            searchQuery || statusFilter !== 'ALL'
              ? 'No sectors match your active filter criteria. Try adjusting your search query or filters.'
              : 'No sector data currently available in this universe.'
          }
        />
      ) : viewMode === 'cards' ? (
        /* Card Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {filteredSectors.map((sector) => {
            const isExpanded = !!expandedSectors[sector.name];
            const constituents = stocksBySector[sector.name.trim().toLowerCase()] || [];
            const StatusIcon = sector.statusIcon || getStatusIcon(sector.status);

            return (
              <div
                key={sector.id}
                className="bg-surface border border-border-primary rounded-2xl shadow-sm hover:shadow-md transition-all flex flex-col justify-between overflow-hidden"
              >
                {/* Sector Card Top Header */}
                <div className="p-5 sm:p-6 space-y-4">
                  <div className="flex justify-between items-start gap-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-surface-secondary text-tx-secondary border border-border-primary">
                          #{sector.rank}
                        </span>
                        <h2 className="text-base sm:text-lg font-heading font-bold text-tx-primary">
                          {sector.name}
                        </h2>
                      </div>
                      <div className="text-xs text-tx-secondary flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5" />
                        <span>
                          {sector.stockCount != null ? `${sector.stockCount} constituent stocks` : 'Stock count unavailable'}
                        </span>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold border ${sector.statusBadgeClass} shrink-0`}>
                      <StatusIcon className="w-3 h-3" />
                      <span>{sector.status}</span>
                    </span>
                  </div>

                  {/* Relative Strength vs Benchmark Indicator */}
                  <div className="bg-surface-secondary/60 rounded-xl p-3 border border-border-primary/50 text-xs space-y-1.5">
                    <div className="flex justify-between items-center text-tx-secondary">
                      <span>Relative Strength vs NIFTY:</span>
                      <span className="font-mono font-semibold text-tx-primary">
                        {sector.relativeStrengthStatus === 'VALID' && sector.relativeStrength != null ? (
                          sector.relativeStrengthType === 'ratio'
                            ? `${sector.relativeStrength.toFixed(2)}x`
                            : formatPercent(sector.relativeStrength * 100, { showSign: true, decimals: 1 })
                        ) : (
                          <span className="text-tx-muted font-normal">Unavailable</span>
                        )}
                      </span>
                    </div>

                    {/* Visual strength bar */}
                    {sector.relativeStrength != null && (
                      <div className="w-full bg-border-primary/40 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            sector.status === 'Outperforming'
                              ? 'bg-accent-green'
                              : sector.status === 'Lagging'
                              ? 'bg-accent-red'
                              : 'bg-accent-warning'
                          }`}
                          style={{
                            width: `${Math.min(
                              Math.max(
                                sector.relativeStrengthType === 'ratio'
                                  ? ((sector.relativeStrength - 0.8) / 0.4) * 100
                                  : ((sector.relativeStrength + 0.1) / 0.2) * 100,
                                10
                              ),
                              100
                            )}%`
                          }}
                        />
                      </div>
                    )}
                  </div>

                  {/* Multi-Timeframe Performance Matrix */}
                  <div className="grid grid-cols-3 gap-2 pt-1 text-center">
                    <div className="bg-surface-secondary/40 rounded-lg p-2 border border-border-primary/40">
                      <div className="text-[10px] text-tx-secondary font-medium uppercase mb-0.5">21D (1M)</div>
                      <div>{renderPerformanceBadge(sector.performance_21d)}</div>
                    </div>
                    <div className="bg-surface-secondary/40 rounded-lg p-2 border border-border-primary/40">
                      <div className="text-[10px] text-tx-secondary font-medium uppercase mb-0.5">63D (3M)</div>
                      <div>{renderPerformanceBadge(sector.performance_63d)}</div>
                    </div>
                    <div className="bg-surface-secondary/40 rounded-lg p-2 border border-border-primary/40">
                      <div className="text-[10px] text-tx-secondary font-medium uppercase mb-0.5">126D (6M)</div>
                      <div>{renderPerformanceBadge(sector.performance_126d)}</div>
                    </div>
                  </div>
                </div>

                {/* Constituent Stocks Drawer Toggle */}
                <div className="border-t border-border-primary bg-surface-secondary/30">
                  <button
                    type="button"
                    onClick={() => toggleSectorExpand(sector.name)}
                    aria-expanded={isExpanded}
                    className="w-full px-5 py-3 flex items-center justify-between text-xs font-semibold text-tx-secondary hover:text-tx-primary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green cursor-pointer"
                  >
                    <span className="flex items-center gap-1.5">
                      <BarChart3 className="w-3.5 h-3.5 text-accent-green" />
                      <span>Constituent Stocks ({constituents.length})</span>
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-tx-secondary" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-tx-secondary" />
                    )}
                  </button>

                  {/* Expanded Constituent List */}
                  {isExpanded && (
                    <div className="px-5 pb-5 pt-1 space-y-2 border-t border-border-primary/40 animate-fade-in">
                      {constituents.length > 0 ? (
                        <div className="space-y-1.5 max-h-60 overflow-y-auto sidebar-scroll pr-1">
                          {constituents.map((stock) => (
                            <Link
                              key={stock.symbol}
                              to={`/stocks/${stock.symbol}`}
                              className="flex items-center justify-between p-2 rounded-xl bg-surface hover:bg-surface-secondary border border-border-primary/50 transition-colors group"
                            >
                              <div className="min-w-0 pr-2">
                                <div className="flex items-center gap-1.5">
                                  <span className="font-mono font-bold text-xs text-tx-primary group-hover:text-accent-green transition-colors">
                                    {stock.symbol}
                                  </span>
                                  {stock.recommendation && (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-accent-green/10 text-accent-green border border-accent-green/20">
                                      {stock.recommendation}
                                    </span>
                                  )}
                                </div>
                                <div className="text-[11px] text-tx-secondary truncate">
                                  {stock.company_name}
                                </div>
                              </div>
                              <div className="text-right shrink-0">
                                <div className="font-mono font-semibold text-xs text-tx-primary">
                                  {formatCurrency(stock.current_price)}
                                </div>
                                <div className="text-[11px] font-mono">
                                  {renderPerformanceBadge(stock.change_percent)}
                                </div>
                              </div>
                            </Link>
                          ))}
                        </div>
                      ) : (
                        <div className="p-3 bg-surface-secondary/60 rounded-xl text-center text-xs text-tx-secondary border border-border-primary/50">
                          <Info className="w-4 h-4 text-tx-secondary mx-auto mb-1 opacity-70" />
                          <span>No constituent stocks available for this sector in the current universe.</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Tabular Data View */
        <div className="bg-surface border border-border-primary rounded-2xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-surface-secondary/70 border-b border-border-primary text-tx-secondary uppercase text-[11px] font-semibold tracking-wider">
                <tr>
                  <th scope="col" className="py-3.5 px-4 font-semibold">Rank & Sector</th>
                  <th scope="col" className="py-3.5 px-3 font-semibold text-center">Status</th>
                  <th scope="col" className="py-3.5 px-3 font-semibold text-right">RS vs NIFTY</th>
                  <th scope="col" className="py-3.5 px-3 font-semibold text-right">21D (1M)</th>
                  <th scope="col" className="py-3.5 px-3 font-semibold text-right">63D (3M)</th>
                  <th scope="col" className="py-3.5 px-3 font-semibold text-right">126D (6M)</th>
                  <th scope="col" className="py-3.5 px-4 font-semibold text-center">Stocks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-primary/60">
                {filteredSectors.map((sector) => {
                  const isExpanded = !!expandedSectors[sector.name];
                  const constituents = stocksBySector[sector.name.trim().toLowerCase()] || [];
                  const StatusIcon = sector.statusIcon || getStatusIcon(sector.status);

                  return (
                    <React.Fragment key={sector.id}>
                      <tr 
                        onClick={() => toggleSectorExpand(sector.name)}
                        className="hover:bg-surface-secondary/40 transition-colors cursor-pointer group"
                      >
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-tx-secondary px-1.5 py-0.5 rounded bg-surface-secondary">
                              #{sector.rank}
                            </span>
                            <div>
                              <span className="font-semibold text-tx-primary group-hover:text-accent-green transition-colors">
                                {sector.name}
                              </span>
                              <div className="text-[11px] text-tx-secondary">
                                {sector.stockCount != null ? `${sector.stockCount} constituents` : 'Count unavail.'}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${sector.statusBadgeClass}`}>
                            <StatusIcon className="w-3 h-3" />
                            <span>{sector.status}</span>
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-right font-mono font-medium text-tx-primary">
                          {sector.relativeStrengthStatus === 'VALID' && sector.relativeStrength != null ? (
                            sector.relativeStrengthType === 'ratio'
                              ? `${sector.relativeStrength.toFixed(2)}x`
                              : formatPercent(sector.relativeStrength * 100, { showSign: true, decimals: 1 })
                          ) : (
                            <span className="text-tx-muted text-xs">Unavailable</span>
                          )}
                        </td>
                        <td className="py-3.5 px-3 text-right">
                          {renderPerformanceBadge(sector.performance_21d)}
                        </td>
                        <td className="py-3.5 px-3 text-right">
                          {renderPerformanceBadge(sector.performance_63d)}
                        </td>
                        <td className="py-3.5 px-3 text-right">
                          {renderPerformanceBadge(sector.performance_126d)}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleSectorExpand(sector.name);
                            }}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-secondary hover:bg-surface-secondary/80 text-tx-primary text-xs font-medium border border-border-primary transition-colors cursor-pointer"
                          >
                            <span>{constituents.length}</span>
                            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          </button>
                        </td>
                      </tr>

                      {/* Expandable Constituent Stocks Accordion Row */}
                      {isExpanded && (
                        <tr className="bg-surface-secondary/20 border-b border-border-primary/70">
                          <td colSpan={7} className="p-4 sm:p-6">
                            <div className="bg-surface border border-border-primary rounded-xl p-4 shadow-2xs space-y-3">
                              <div className="flex items-center justify-between text-xs font-semibold text-tx-secondary border-b border-border-primary pb-2">
                                <span>Constituent Stocks in {sector.name}</span>
                                <span>{constituents.length} available</span>
                              </div>

                              {constituents.length > 0 ? (
                                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2.5">
                                  {constituents.map(stock => (
                                    <Link
                                      key={stock.symbol}
                                      to={`/stocks/${stock.symbol}`}
                                      className="p-2.5 rounded-xl bg-surface-secondary/50 hover:bg-surface-secondary border border-border-primary/60 transition-all flex flex-col justify-between group"
                                    >
                                      <div className="flex items-center justify-between gap-1 mb-1">
                                        <span className="font-mono font-bold text-xs text-tx-primary group-hover:text-accent-green transition-colors">
                                          {stock.symbol}
                                        </span>
                                        <ExternalLink className="w-3 h-3 text-tx-secondary opacity-0 group-hover:opacity-100 transition-opacity" />
                                      </div>
                                      <div className="text-[11px] text-tx-secondary truncate mb-2">
                                        {stock.company_name}
                                      </div>
                                      <div className="flex items-center justify-between text-xs pt-1 border-t border-border-primary/40 font-mono">
                                        <span className="font-semibold text-tx-primary">
                                          {formatCurrency(stock.current_price)}
                                        </span>
                                        <span>
                                          {renderPerformanceBadge(stock.change_percent)}
                                        </span>
                                      </div>
                                    </Link>
                                  ))}
                                </div>
                              ) : (
                                <div className="text-center py-4 text-xs text-tx-secondary">
                                  No constituent stocks found for this sector in the active database.
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Footer Info Notice */}
      <div className="bg-surface rounded-2xl border border-border-primary p-4 sm:p-5 text-xs text-tx-secondary flex items-start gap-3">
        <Info className="w-5 h-5 text-accent-teal shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-semibold text-tx-primary">Sector Methodology & Data Provenance</div>
          <p>
            Sector returns are computed as an equal-weighted aggregation of constituent equity returns over 21D (1 Month), 63D (3 Months), and 126D (6 Months) trading periods. Relative strength indicates percentage momentum vs the NIFTY 50 baseline (1.00x). Where benchmark feeds are pending integration, indicators explicitly display unavailable status rather than simulating synthetic values.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SectorExplorer;
