import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  getMarketIndices,
  getOpportunities,
  getSectors,
  getDataHealth
} from '../services/api';
import MetricCard from '../components/MetricCard';
import OpportunityTable from '../components/OpportunityTable';
import SectorList from '../components/SectorList';
import { LoadingState, ErrorState } from '../components/StateComponents';
import {
  RefreshCw,
  TrendingUp,
  Activity,
  Database,
  CheckCircle2,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';

const IS_MOCK_MODE = import.meta.env.VITE_USE_MOCK_DATA === 'true';

const Sparkline = ({ isPositive = true }) => {
  const color = isPositive ? 'text-accent-green' : 'text-accent-red';
  const pathD = isPositive
    ? 'M0 28 L20 22 L40 24 L60 14 L80 16 L100 6'
    : 'M0 8 L20 14 L40 12 L60 22 L80 18 L100 28';
  const fillD = isPositive
    ? 'M0 28 L20 22 L40 24 L60 14 L80 16 L100 6 V36 H0 Z'
    : 'M0 8 L20 14 L40 12 L60 22 L80 18 L100 28 V36 H0 Z';

  return (
    <svg
      viewBox="0 0 100 36"
      className={`w-20 sm:w-24 h-9 ${color} shrink-0`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d={pathD}
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d={fillD}
        fill="currentColor"
        fillOpacity="0.12"
      />
    </svg>
  );
};

const Dashboard = () => {
  const [indicesState, setIndicesState] = useState({ data: null, loading: true, error: null });
  const [oppsState, setOppsState] = useState({ data: null, loading: true, error: null });
  const [sectorsState, setSectorsState] = useState({ data: null, loading: true, error: null });
  const [healthState, setHealthState] = useState({ data: null, loading: true, error: null });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(() => new Date());

  const isMountedRef = useRef(true);

  // Independent fetch handlers for graceful partial degradation
  const fetchIndices = useCallback(async () => {
    setIndicesState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await getMarketIndices();
      if (isMountedRef.current) {
        setIndicesState({ data: res, loading: false, error: null });
      }
    } catch (err) {
      if (isMountedRef.current) {
        setIndicesState({
          data: null,
          loading: false,
          error: err.message || 'Market index service unavailable.'
        });
      }
    }
  }, []);

  const fetchOpportunities = useCallback(async () => {
    setOppsState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await getOpportunities();
      if (isMountedRef.current) {
        setOppsState({
          data: Array.isArray(res) ? res : res?.opportunities || [],
          loading: false,
          error: null
        });
      }
    } catch (err) {
      if (isMountedRef.current) {
        setOppsState({
          data: null,
          loading: false,
          error: err.message || 'Opportunity screening service unavailable.'
        });
      }
    }
  }, []);

  const fetchSectors = useCallback(async () => {
    setSectorsState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await getSectors();
      if (isMountedRef.current) {
        setSectorsState({
          data: Array.isArray(res) ? res : res?.sectors || [],
          loading: false,
          error: null
        });
      }
    } catch (err) {
      if (isMountedRef.current) {
        setSectorsState({
          data: null,
          loading: false,
          error: err.message || 'Sector performance service unavailable.'
        });
      }
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    setHealthState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await getDataHealth();
      if (isMountedRef.current) {
        setHealthState({ data: res, loading: false, error: null });
      }
    } catch (err) {
      if (isMountedRef.current) {
        setHealthState({
          data: null,
          loading: false,
          error: err.message || 'Pipeline health monitoring service unavailable.'
        });
      }
    }
  }, []);

  // Global refresh triggers all 4 services concurrently
  const refreshAll = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.allSettled([
      fetchIndices(),
      fetchOpportunities(),
      fetchSectors(),
      fetchHealth()
    ]);
    if (isMountedRef.current) {
      setIsRefreshing(false);
      setLastRefreshed(new Date());
    }
  }, [fetchIndices, fetchOpportunities, fetchSectors, fetchHealth]);

  useEffect(() => {
    isMountedRef.current = true;

    // Initial fetch on mount without cascading renders
    const init = async () => {
      await Promise.allSettled([
        fetchIndices(),
        fetchOpportunities(),
        fetchSectors(),
        fetchHealth()
      ]);
      if (isMountedRef.current) {
        setLastRefreshed(new Date());
      }
    };
    init();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchIndices, fetchOpportunities, fetchSectors, fetchHealth]);

  const indices = indicesState.data;

  // Format index changes cleanly
  const formatIndexDisplay = (indexObj) => {
    if (!indexObj || indexObj.value == null) return null;
    const isPos = indexObj.is_positive ?? (indexObj.change_percent >= 0);
    const pct = indexObj.change_percent != null
      ? `${indexObj.change_percent > 0 ? '+' : ''}${Number(indexObj.change_percent).toFixed(2)}%`
      : null;
    const abs = indexObj.change_absolute != null
      ? `${indexObj.change_absolute > 0 ? '+' : ''}${Number(indexObj.change_absolute).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : null;

    return {
      value: Number(indexObj.value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
      change: pct,
      changeAbsolute: abs,
      isPositive: isPos
    };
  };

  const niftyDisplay = formatIndexDisplay(indices?.nifty50);
  const sensexDisplay = formatIndexDisplay(indices?.sensex);

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header with Status & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border-primary/50">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-heading font-bold text-tx-primary tracking-tight">
              Market Intelligence
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
          </div>
          <p className="text-tx-secondary text-xs sm:text-sm mt-1">
            Indian Equities Â· 50-Stock Universe Â· Swing Horizon 3â€“8 Weeks
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right hidden sm:block">
            <div className="text-[11px] text-tx-secondary">Last updated</div>
            <div className="text-xs font-mono font-medium text-tx-primary">
              {lastRefreshed ? lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'â€”'}
            </div>
          </div>
          <button
            type="button"
            onClick={refreshAll}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface border border-border-primary hover:bg-surface-secondary text-tx-primary text-xs sm:text-sm font-medium transition-colors shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green disabled:opacity-50"
            title="Refresh dashboard data"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-accent-green ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* Top Row: Market Indices & Overview */}
      <section aria-labelledby="indices-heading">
        <h2 id="indices-heading" className="sr-only">Market Indices and Overview</h2>
        {indicesState.loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <MetricCard title="NIFTY 50" loading />
            <MetricCard title="SENSEX" loading />
            <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm min-h-[140px] animate-pulse">
              <div className="h-4 bg-surface-secondary rounded w-28 mb-3"></div>
              <div className="h-6 bg-surface-secondary rounded w-36 mb-2"></div>
              <div className="h-3 bg-surface-secondary rounded w-48"></div>
            </div>
          </div>
        ) : indicesState.error ? (
          <div className="bg-surface rounded-xl border border-border-primary p-6 shadow-sm">
            <ErrorState
              compact
              title="Market Indices Unavailable"
              message={indicesState.error}
              onRetry={fetchIndices}
            />
          </div>
        ) : !indices || (!niftyDisplay && !sensexDisplay) ? (
          <div className="bg-surface rounded-xl border border-border-primary p-6 shadow-sm">
            <div className="text-center text-tx-secondary text-sm">
              Index data is currently unavailable.
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* NIFTY 50 Card */}
            {niftyDisplay ? (
              <MetricCard
                title="NIFTY 50"
                value={niftyDisplay.value}
                change={niftyDisplay.change}
                changeAbsolute={niftyDisplay.changeAbsolute}
                isPositive={niftyDisplay.isPositive}
                subtitle="today"
                extra={<Sparkline isPositive={niftyDisplay.isPositive} />}
              />
            ) : (
              <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm flex flex-col justify-center">
                <h3 className="text-sm font-semibold text-tx-secondary mb-1">NIFTY 50</h3>
                <p className="text-xs text-tx-secondary">Index benchmark unavailable</p>
              </div>
            )}

            {/* SENSEX Card */}
            {sensexDisplay ? (
              <MetricCard
                title="SENSEX"
                value={sensexDisplay.value}
                change={sensexDisplay.change}
                changeAbsolute={sensexDisplay.changeAbsolute}
                isPositive={sensexDisplay.isPositive}
                subtitle="today"
                extra={<Sparkline isPositive={sensexDisplay.isPositive} />}
              />
            ) : (
              <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm flex flex-col justify-center">
                <h3 className="text-sm font-semibold text-tx-secondary mb-1">SENSEX</h3>
                <p className="text-xs text-tx-secondary">Index benchmark unavailable</p>
              </div>
            )}

            {/* Market Condition / Market Overview Card */}
            {indices.condition ? (
              <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm flex flex-col justify-between transition-colors min-h-[140px]">
                <div>
                  <div className="flex justify-between items-start mb-3">
                    <h3 className="text-sm font-semibold text-tx-secondary uppercase tracking-wide">
                      Market Condition
                    </h3>
                    {indices.condition.label && (
                      <span className="px-2.5 py-0.5 bg-accent-green/10 text-accent-green text-xs font-semibold rounded-full border border-accent-green/20">
                        {indices.condition.label}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 mb-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-accent-green animate-pulse"></div>
                    <div className="text-2xl font-heading font-bold text-tx-primary">
                      {indices.condition.status || 'Active'}
                    </div>
                  </div>

                  {indices.condition.description && (
                    <p className="text-xs text-tx-secondary mb-3">
                      {indices.condition.description}
                    </p>
                  )}
                </div>

                {indices.condition.advancing != null && indices.condition.declining != null && (
                  <div className="pt-2 border-t border-border-primary/60 space-y-1.5 text-xs">
                    <div className="flex justify-between text-tx-secondary">
                      <span>Advancing: <strong className="text-accent-green font-medium font-mono">{indices.condition.advancing.toLocaleString()}</strong></span>
                      <span>Declining: <strong className="text-accent-red font-medium font-mono">{indices.condition.declining.toLocaleString()}</strong></span>
                    </div>
                    {/* Market Breadth Progress Bar */}
                    <div className="w-full bg-surface-secondary h-1.5 rounded-full overflow-hidden flex">
                      <div
                        className="bg-accent-green h-full"
                        style={{
                          width: `${(indices.condition.advancing / (indices.condition.advancing + indices.condition.declining)) * 100}%`
                        }}
                      />
                      <div
                        className="bg-accent-red h-full"
                        style={{
                          width: `${(indices.condition.declining / (indices.condition.advancing + indices.condition.declining)) * 100}%`
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Neutral Market Scope Card when condition object is absent */
              <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm flex flex-col justify-between transition-colors min-h-[140px]">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-sm font-semibold text-tx-secondary uppercase tracking-wide">
                      Universe Overview
                    </h3>
                    <span className="px-2 py-0.5 bg-surface-secondary text-tx-secondary text-xs rounded border border-border-primary">
                      NIFTY 50 Universe
                    </span>
                  </div>
                  <div className="text-lg font-heading font-bold text-tx-primary mb-1">
                    50 Liquid Equities
                  </div>
                  <p className="text-xs text-tx-secondary">
                    Continuously ranked by technical momentum, sector leadership, financial durability, and reward-to-risk setups.
                  </p>
                </div>
                <div className="pt-3 border-t border-border-primary/60 flex items-center justify-between text-xs">
                  <span className="text-tx-secondary">Swing horizon: 3â€“8 weeks</span>
                  <Link to="/stocks" className="text-accent-green hover:underline flex items-center">
                    Browse Stocks <ChevronRight className="w-3 h-3 ml-0.5" />
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Middle Row: Top Swing Opportunities & Leading Sectors */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        <div className="lg:col-span-2">
          <OpportunityTable
            opportunities={oppsState.data}
            loading={oppsState.loading}
            error={oppsState.error}
            onRetry={fetchOpportunities}
          />
        </div>
        <div className="lg:col-span-1">
          <SectorList
            sectors={sectorsState.data}
            loading={sectorsState.loading}
            error={sectorsState.error}
            onRetry={fetchSectors}
          />
        </div>
      </section>

      {/* Bottom Row: Methodology Context & Data Health */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        {/* Methodological Context Card */}
        <div className="lg:col-span-2 bg-surface rounded-2xl border border-border-primary shadow-sm p-6 flex flex-col justify-between transition-colors">
          <div>
            <div className="flex justify-between items-start mb-3">
              <div>
                <h2 className="text-lg font-heading font-bold text-tx-primary">
                  Multi-Factor Decision Engine
                </h2>
                <p className="text-xs text-tx-secondary mt-0.5">
                  How the Opportunity Score is evaluated for systematic swing trading
                </p>
              </div>
              <Link
                to="/opportunities"
                className="text-accent-green text-sm font-medium hover:text-accent-green/80 flex items-center shrink-0 ml-4 transition-colors"
              >
                Full screener <ChevronRight className="w-4 h-4 ml-0.5" />
              </Link>
            </div>

            <p className="text-sm text-tx-secondary mb-5 leading-relaxed">
              Every stock in the universe is evaluated across four quantitative pillars to identify high-probability swing opportunities with asymmetric upside:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 rounded-xl bg-surface-secondary/40 border border-border-primary/60">
                <div className="flex items-center gap-2 mb-1.5 font-semibold text-tx-primary">
                  <Activity className="w-4 h-4 text-accent-green shrink-0" />
                  <span>Technical Momentum</span>
                </div>
                <p className="text-tx-secondary leading-normal">
                  EMA 20/50 trend alignment, RSI momentum confirmation in the 40â€“65 pull-back zone, and ATR volatility bands.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-secondary/40 border border-border-primary/60">
                <div className="flex items-center gap-2 mb-1.5 font-semibold text-tx-primary">
                  <ShieldCheck className="w-4 h-4 text-accent-teal shrink-0" />
                  <span>Financial Quality</span>
                </div>
                <p className="text-tx-secondary leading-normal">
                  Consistent ROE (&gt;12%), sustainable ROCE, disciplined debt-to-equity ratios, and operating margin stability.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-secondary/40 border border-border-primary/60">
                <div className="flex items-center gap-2 mb-1.5 font-semibold text-tx-primary">
                  <TrendingUp className="w-4 h-4 text-accent-orange shrink-0" />
                  <span>Sector Leadership</span>
                </div>
                <p className="text-tx-secondary leading-normal">
                  Relative strength vs NIFTY 50 benchmark (&gt;1.05x). Opportunities in leading sectors carry higher follow-through.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-surface-secondary/40 border border-border-primary/60">
                <div className="flex items-center gap-2 mb-1.5 font-semibold text-tx-primary">
                  <CheckCircle2 className="w-4 h-4 text-accent-green shrink-0" />
                  <span>Risk & Trade Quality</span>
                </div>
                <p className="text-tx-secondary leading-normal">
                  Strict &ge;1.5x Reward-to-Risk ratio with predefined entry zones, technical stop-losses, and profit targets.
                </p>
              </div>
            </div>
          </div>

          <div className="pt-4 mt-6 border-t border-border-primary flex flex-wrap items-center justify-between gap-3 text-xs text-tx-secondary">
            <span>Holding horizon: 3 to 8 weeks Â· Weekly rebalancing</span>
            <div className="flex items-center gap-4">
              <Link to="/opportunities" className="text-accent-green hover:underline">
                Explore Opportunities â†’
              </Link>
              <Link to="/stocks" className="text-tx-primary hover:underline">
                Browse All Stocks â†’
              </Link>
            </div>
          </div>
        </div>

        {/* Data Pipeline Health Card */}
        <div className="lg:col-span-1 bg-surface rounded-2xl border border-border-primary shadow-sm p-6 flex flex-col justify-between transition-colors">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-accent-teal" />
                <h2 className="text-lg font-heading font-bold text-tx-primary">Data Health</h2>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-secondary text-tx-secondary border border-border-primary">
                Daily EOD
              </span>
            </div>

            {healthState.loading ? (
              <LoadingState compact message="Checking data health..." />
            ) : healthState.error ? (
              <ErrorState
                compact
                title="Data Health Unavailable"
                message={healthState.error}
                onRetry={fetchHealth}
              />
            ) : healthState.data ? (
              <div className="space-y-3.5 text-sm">
                <div className="flex justify-between items-center pb-2.5 border-b border-border-primary/50">
                  <span className="text-tx-secondary text-xs">Market Price Data</span>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-accent-green/10 text-accent-green text-xs font-medium rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-green"></span>
                    {healthState.data.market_data || 'Healthy'}
                  </span>
                </div>

                <div className="flex justify-between items-center pb-2.5 border-b border-border-primary/50">
                  <span className="text-tx-secondary text-xs">Technical Indicators</span>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-accent-green/10 text-accent-green text-xs font-medium rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-green"></span>
                    {healthState.data.technical_data || 'Healthy'}
                  </span>
                </div>

                <div className="flex justify-between items-center pb-2.5 border-b border-border-primary/50">
                  <span className="text-tx-secondary text-xs">Financial Fundamentals</span>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-accent-green/10 text-accent-green text-xs font-medium rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-green"></span>
                    {healthState.data.financial_data || 'Healthy'}
                  </span>
                </div>

                {healthState.data.universe_count && (
                  <div className="flex justify-between items-center pb-2.5 border-b border-border-primary/50 text-xs">
                    <span className="text-tx-secondary">Universe Size</span>
                    <span className="font-mono font-medium text-tx-primary">
                      {healthState.data.universe_count} stocks
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-tx-secondary p-4 text-center">
                Data pipeline health status unavailable.
              </div>
            )}
          </div>

          <div className="pt-4 mt-6 border-t border-border-primary text-xs text-tx-muted space-y-1">
            <div className="flex justify-between">
              <span>Pipeline Sync:</span>
              <span className="text-tx-secondary">EOD Batch (Daily)</span>
            </div>
            {healthState.data?.last_updated && (
              <div className="flex justify-between">
                <span>Last Updated:</span>
                <span className="font-mono text-tx-secondary">
                  {new Date(healthState.data.last_updated).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;

