import React from 'react';
import {
  TrendingUp,
  Activity,
  Layers,
  Info,
  SlidersHorizontal,
  Compass,
} from 'lucide-react';
import {
  getRsiZone,
  getMacdStatus,
  getEmaAlignment,
} from '../utils/technicalIndicators';
import { formatCurrency, formatPercent } from '../utils/formatters';

/**
 * TechnicalAnalysisCard
 * 
 * Comprehensive technical indicators overview component implementing Phase 15 requirements:
 * - Exponential Moving Averages (EMA 20, 50, 200) with multi-horizon trend alignment
 * - Relative Strength Index (RSI 14) with zone classification and non-guaranteed educational note
 * - MACD (12, 26, 9) with momentum velocity and histogram breakdown
 * - Independent indicator visibility toggles
 * - Non-fabricated handling for insufficient data
 * - Responsive, accessible, and theme-tailored
 */
const TechnicalAnalysisCard = ({
  stock = {},
  indicators = null,
  activeIndicators = {
    ema20: true,
    ema50: true,
    ema200: false,
    rsi: true,
    macd: true,
  },
  onToggleIndicator = () => {},
  className = '',
}) => {
  const latest = indicators?.latest;
  const sufficiency = indicators?.sufficiency;
  const currentPrice = stock.currentPrice != null ? Number(stock.currentPrice) : latest?.close;

  // Calculate distance from price to each EMA
  const getEmaDiff = (emaVal) => {
    if (currentPrice == null || emaVal == null) return null;
    const diff = currentPrice - emaVal;
    const pct = (diff / emaVal) * 100;
    return { diff, pct, isAbove: diff >= 0 };
  };

  const ema20Diff = getEmaDiff(latest?.ema20);
  const ema50Diff = getEmaDiff(latest?.ema50);
  const ema200Diff = getEmaDiff(latest?.ema200);

  const emaAlignment = getEmaAlignment(
    currentPrice,
    latest?.ema20 ?? null,
    latest?.ema50 ?? null,
    latest?.ema200 ?? null
  );

  const rsiZone = getRsiZone(latest?.rsi ?? null);
  const macdStatus = getMacdStatus(
    latest?.macd ?? null,
    latest?.signal ?? null,
    latest?.histogram ?? null
  );

  return (
    <div className={`bg-surface rounded-2xl border border-border-primary p-5 sm:p-7 shadow-sm transition-colors ${className}`}>
      {/* Card Header & Global Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-border-primary">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h2 className="font-heading font-bold text-xl sm:text-2xl text-tx-primary tracking-tight flex items-center gap-2">
              <Compass className="w-5 h-5 text-accent-teal" />
              Technical Analysis Interface
            </h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-accent-teal/10 text-accent-teal font-medium border border-accent-teal/20">
              Phase 15 Engine
            </span>
          </div>
          <p className="text-xs sm:text-sm text-tx-secondary">
            Descriptive historical indicators computed from end-of-day closing prices.
          </p>
        </div>

        {/* Quick Indicator Visibility Toggles */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-semibold text-tx-muted uppercase tracking-wider mr-1 flex items-center gap-1">
            <SlidersHorizontal className="w-3 h-3" />
            Overlays:
          </span>

          {/* EMA 20 Toggle */}
          <button
            type="button"
            onClick={() => onToggleIndicator('ema20')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
              activeIndicators.ema20
                ? 'bg-[#38BDF8]/15 text-[#38BDF8] border-[#38BDF8]/40 font-semibold'
                : 'bg-surface-secondary text-tx-muted border-border-primary hover:text-tx-primary'
            }`}
            aria-pressed={activeIndicators.ema20}
            title="Toggle EMA 20 on chart"
          >
            <span className="w-2 h-2 rounded-full bg-[#38BDF8]"></span>
            <span>EMA 20</span>
          </button>

          {/* EMA 50 Toggle */}
          <button
            type="button"
            onClick={() => onToggleIndicator('ema50')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
              activeIndicators.ema50
                ? 'bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/40 font-semibold'
                : 'bg-surface-secondary text-tx-muted border-border-primary hover:text-tx-primary'
            }`}
            aria-pressed={activeIndicators.ema50}
            title="Toggle EMA 50 on chart"
          >
            <span className="w-2 h-2 rounded-full bg-[#F59E0B]"></span>
            <span>EMA 50</span>
          </button>

          {/* EMA 200 Toggle */}
          <button
            type="button"
            onClick={() => onToggleIndicator('ema200')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
              activeIndicators.ema200
                ? 'bg-[#A855F7]/15 text-[#A855F7] border-[#A855F7]/40 font-semibold'
                : 'bg-surface-secondary text-tx-muted border-border-primary hover:text-tx-primary'
            }`}
            aria-pressed={activeIndicators.ema200}
            title="Toggle EMA 200 on chart"
          >
            <span className="w-2 h-2 rounded-full bg-[#A855F7]"></span>
            <span>EMA 200</span>
          </button>

          {/* RSI Toggle */}
          <button
            type="button"
            onClick={() => onToggleIndicator('rsi')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
              activeIndicators.rsi
                ? 'bg-accent-teal/15 text-accent-teal border-accent-teal/40 font-semibold'
                : 'bg-surface-secondary text-tx-muted border-border-primary hover:text-tx-primary'
            }`}
            aria-pressed={activeIndicators.rsi}
            title="Toggle RSI sub-panel"
          >
            <Activity className="w-3 h-3" />
            <span>RSI (14)</span>
          </button>

          {/* MACD Toggle */}
          <button
            type="button"
            onClick={() => onToggleIndicator('macd')}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
              activeIndicators.macd
                ? 'bg-accent-green/15 text-accent-green border-accent-green/40 font-semibold'
                : 'bg-surface-secondary text-tx-muted border-border-primary hover:text-tx-primary'
            }`}
            aria-pressed={activeIndicators.macd}
            title="Toggle MACD sub-panel"
          >
            <Layers className="w-3 h-3" />
            <span>MACD</span>
          </button>
        </div>
      </div>

      {/* Main Indicators Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
        {/* 1. Exponential Moving Averages Panel */}
        <div className="bg-surface-secondary/50 rounded-xl border border-border-primary/80 p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-border-primary/60">
              <span className="font-heading font-semibold text-sm text-tx-primary flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-accent-teal" />
                Moving Averages (EMA)
              </span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${emaAlignment.badgeClass}`}>
                {emaAlignment.label}
              </span>
            </div>

            <p className="text-xs text-tx-secondary mb-4 leading-relaxed">
              Trend velocity benchmarks across short (20D), medium (50D), and long-term (200D) horizons.
            </p>

            {/* EMA List with metrics */}
            <div className="space-y-3 font-mono text-xs">
              {/* EMA 20 */}
              <div className="p-2.5 rounded-lg bg-surface border border-border-primary/60 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-1.5 font-sans font-medium text-tx-secondary text-[11px]">
                    <span className="w-2 h-2 rounded-full bg-[#38BDF8]"></span>
                    EMA 20 (Short-term)
                  </div>
                  <div className="text-sm font-bold text-tx-primary mt-0.5">
                    {latest?.ema20 != null ? formatCurrency(latest.ema20) : 'Insufficient Data'}
                  </div>
                </div>
                {ema20Diff && (
                  <div className={`text-right text-[11px] font-semibold ${ema20Diff.isAbove ? 'text-accent-green' : 'text-accent-red'}`}>
                    <div>{ema20Diff.isAbove ? 'Above' : 'Below'}</div>
                    <div>{formatPercent(ema20Diff.pct)}</div>
                  </div>
                )}
              </div>

              {/* EMA 50 */}
              <div className="p-2.5 rounded-lg bg-surface border border-border-primary/60 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-1.5 font-sans font-medium text-tx-secondary text-[11px]">
                    <span className="w-2 h-2 rounded-full bg-[#F59E0B]"></span>
                    EMA 50 (Medium-term)
                  </div>
                  <div className="text-sm font-bold text-tx-primary mt-0.5">
                    {latest?.ema50 != null ? formatCurrency(latest.ema50) : 'Insufficient Data'}
                  </div>
                </div>
                {ema50Diff && (
                  <div className={`text-right text-[11px] font-semibold ${ema50Diff.isAbove ? 'text-accent-green' : 'text-accent-red'}`}>
                    <div>{ema50Diff.isAbove ? 'Above' : 'Below'}</div>
                    <div>{formatPercent(ema50Diff.pct)}</div>
                  </div>
                )}
              </div>

              {/* EMA 200 */}
              <div className="p-2.5 rounded-lg bg-surface border border-border-primary/60 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-1.5 font-sans font-medium text-tx-secondary text-[11px]">
                    <span className="w-2 h-2 rounded-full bg-[#A855F7]"></span>
                    EMA 200 (Long-term)
                  </div>
                  <div className="text-sm font-bold text-tx-primary mt-0.5">
                    {latest?.ema200 != null ? formatCurrency(latest.ema200) : 'Insufficient Data (< 200D)'}
                  </div>
                </div>
                {ema200Diff ? (
                  <div className={`text-right text-[11px] font-semibold ${ema200Diff.isAbove ? 'text-accent-green' : 'text-accent-red'}`}>
                    <div>{ema200Diff.isAbove ? 'Above' : 'Below'}</div>
                    <div>{formatPercent(ema200Diff.pct)}</div>
                  </div>
                ) : (
                  <span className="text-[10px] text-tx-muted font-sans italic">Requires 200 bars</span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-border-primary/60 text-[11px] text-tx-muted">
            {emaAlignment.description}
          </div>
        </div>

        {/* 2. RSI Panel */}
        <div className="bg-surface-secondary/50 rounded-xl border border-border-primary/80 p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-border-primary/60">
              <span className="font-heading font-semibold text-sm text-tx-primary flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-accent-teal" />
                RSI (14-Period)
              </span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${rsiZone.badgeClass}`}>
                {rsiZone.label}
              </span>
            </div>

            <p className="text-xs text-tx-secondary mb-4 leading-relaxed">
              Measures relative velocity of recent price changes on a normalized 0 to 100 scale.
            </p>

            {/* Gauge / Value Bar */}
            <div className="p-3.5 rounded-lg bg-surface border border-border-primary/60 space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-tx-secondary font-medium">Latest RSI Value</span>
                <span className="font-mono text-2xl font-bold text-tx-primary">
                  {latest?.rsi != null ? latest.rsi.toFixed(2) : '—'}
                </span>
              </div>

              {/* Visual 0-100 Progress Track with 30 & 70 markers */}
              <div className="relative pt-2 pb-1">
                <div className="h-2.5 w-full bg-surface-secondary rounded-full overflow-hidden flex">
                  {/* Oversold zone: 0 to 30 */}
                  <div className="h-full bg-accent-teal/30" style={{ width: '30%' }} title="Oversold Zone (<30)"></div>
                  {/* Neutral zone: 30 to 70 */}
                  <div className="h-full bg-surface-secondary border-x border-border-primary/40" style={{ width: '40%' }} title="Neutral Range (30-70)"></div>
                  {/* Overbought zone: 70 to 100 */}
                  <div className="h-full bg-accent-orange/30" style={{ width: '30%' }} title="Overbought Zone (>70)"></div>
                </div>

                {/* Marker Pin for current RSI */}
                {latest?.rsi != null && (
                  <div
                    className="absolute top-0.5 -translate-x-1/2 flex flex-col items-center"
                    style={{ left: `${Math.min(Math.max(latest.rsi, 0), 100)}%` }}
                  >
                    <div className="w-3 h-3 rounded-full bg-accent-teal border-2 border-surface shadow-xs"></div>
                  </div>
                )}

                {/* Threshold labels */}
                <div className="flex justify-between text-[10px] font-mono text-tx-muted mt-2">
                  <span>0 (Oversold)</span>
                  <span className="text-accent-teal font-semibold">30</span>
                  <span className="text-tx-secondary font-medium">50</span>
                  <span className="text-accent-orange font-semibold">70</span>
                  <span>100 (Overbought)</span>
                </div>
              </div>
            </div>

            {/* Range Breakdown Guide */}
            <div className="mt-3 grid grid-cols-3 gap-1.5 text-[10px] text-center font-medium">
              <div className="p-1.5 rounded bg-surface border border-border-primary/50 text-accent-teal">
                &lt; 30 Oversold
              </div>
              <div className="p-1.5 rounded bg-surface border border-border-primary/50 text-tx-secondary">
                30–70 Neutral
              </div>
              <div className="p-1.5 rounded bg-surface border border-border-primary/50 text-accent-orange">
                &gt; 70 Overbought
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-border-primary/60 text-[11px] text-tx-muted flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 text-accent-teal shrink-0 mt-0.5" />
            <span>
              {rsiZone.description} Not a guaranteed trading signal.
            </span>
          </div>
        </div>

        {/* 3. MACD Panel */}
        <div className="bg-surface-secondary/50 rounded-xl border border-border-primary/80 p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-border-primary/60">
              <span className="font-heading font-semibold text-sm text-tx-primary flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-accent-teal" />
                MACD (12, 26, 9)
              </span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${macdStatus.badgeClass}`}>
                {macdStatus.label}
              </span>
            </div>

            <p className="text-xs text-tx-secondary mb-4 leading-relaxed">
              Moving Average Convergence Divergence tracking directional trend acceleration.
            </p>

            {/* MACD metrics breakdown */}
            <div className="space-y-2.5 font-mono text-xs">
              {/* MACD Line */}
              <div className="p-2.5 rounded-lg bg-surface border border-border-primary/60 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-1.5 font-sans font-medium text-tx-secondary text-[11px]">
                    <span className="w-2.5 h-0.5 bg-[#38BDF8] rounded-full"></span>
                    MACD Line (12 - 26 EMA)
                  </div>
                  <div className="text-sm font-bold text-tx-primary mt-0.5">
                    {latest?.macd != null ? latest.macd.toFixed(2) : 'Insufficient Data'}
                  </div>
                </div>
                <div className="text-right text-[10px] font-sans text-tx-muted">
                  {latest?.macd != null && latest.macd >= 0 ? 'Above Baseline (0)' : 'Below Baseline (0)'}
                </div>
              </div>

              {/* Signal Line */}
              <div className="p-2.5 rounded-lg bg-surface border border-border-primary/60 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-1.5 font-sans font-medium text-tx-secondary text-[11px]">
                    <span className="w-2.5 h-0.5 bg-[#F97316] rounded-full"></span>
                    Signal Line (9 EMA)
                  </div>
                  <div className="text-sm font-bold text-tx-primary mt-0.5">
                    {latest?.signal != null ? latest.signal.toFixed(2) : 'Insufficient Data'}
                  </div>
                </div>
                <div className="text-right text-[10px] font-sans text-tx-muted">
                  Smoothing Trigger
                </div>
              </div>

              {/* Histogram */}
              <div className="p-2.5 rounded-lg bg-surface border border-border-primary/60 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-1.5 font-sans font-medium text-tx-secondary text-[11px]">
                    <span className={`w-2 h-2 rounded-xs ${latest?.histogram != null && latest.histogram >= 0 ? 'bg-accent-green' : 'bg-accent-red'}`}></span>
                    MACD Histogram
                  </div>
                  <div className={`text-sm font-bold mt-0.5 ${latest?.histogram != null && latest.histogram >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                    {latest?.histogram != null ? (latest.histogram >= 0 ? '+' : '') + latest.histogram.toFixed(2) : '—'}
                  </div>
                </div>
                <div className="text-right text-[10px] font-sans font-medium">
                  {latest?.histogram != null && latest.histogram >= 0 ? (
                    <span className="text-accent-green">Positive Spread</span>
                  ) : (
                    <span className="text-accent-red">Negative Spread</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-border-primary/60 text-[11px] text-tx-muted">
            {macdStatus.description}
          </div>
        </div>
      </div>

      {/* Footer Notice: Educational & Transparent Data Label */}
      <div className="mt-6 pt-4 border-t border-border-primary flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-tx-muted">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-accent-teal shrink-0" />
          <span>
            Technical indicators are mathematical derivations of historical prices. They do not predict future market movements or guarantee profits.
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-medium shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-teal"></span>
          <span>{sufficiency?.totalBars ? `${sufficiency.totalBars} EOD Trading Days` : 'Deterministic EOD Analysis'}</span>
        </div>
      </div>
    </div>
  );
};

export default TechnicalAnalysisCard;
