/**
 * @file EquityCurveChart.jsx
 * @description Interactive native SVG chart for portfolio equity growth and drawdown visualization.
 *
 * FEATURES:
 *   - Native responsive SVG with high-DPI crisp rendering
 *   - Toggle between Equity Curve (₹), Drawdown Profile (%), or Split Dual-Pane View
 *   - Interactive pointer hover tracking with vertical crosshair and tooltip
 *   - Time range controls (ALL, 6M, 3M) when supported by series length
 *   - Light/Dark theme awareness via CSS tokens
 *   - Graceful fallback when equity time-series is unavailable
 */

import React, { useState, useMemo, useRef, useCallback } from 'react';
import { AlertCircle, Calendar } from 'lucide-react';
import { formatCurrency, formatPercent } from '../utils/formatters';
import {
  validateEquitySeries,
  filterEquitySeriesByRange,
  calculateEquityScales,
} from '../utils/performanceHelpers';

export default function EquityCurveChart({
  series = [],
  className = '',
  title = 'Equity Growth & Drawdown Curve',
}) {
  const [range, setRange] = useState('ALL');
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'equity' | 'drawdown'
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const containerRef = useRef(null);

  // Validate raw series
  const validation = useMemo(() => validateEquitySeries(series), [series]);

  // Filter series by active time range
  const filteredSeries = useMemo(() => {
    if (!validation.isValid) return [];
    return filterEquitySeriesByRange(validation.cleanSeries, range);
  }, [validation, range]);

  // Container dimensions
  const width = 800;
  const height = viewMode === 'split' ? 340 : 260;
  const margin = useMemo(() => ({ top: 20, right: 70, bottom: 35, left: 24 }), []);

  const chartWidth = Math.max(width - margin.left - margin.right, 50);

  // Split view heights: Equity gets top 65%, Drawdown gets bottom 35%
  const equityHeight = viewMode === 'split' ? 190 : (viewMode === 'equity' ? 200 : 0);
  const drawdownHeight = viewMode === 'split' ? 80 : (viewMode === 'drawdown' ? 200 : 0);
  const gap = viewMode === 'split' ? 15 : 0;

  // Scales for Equity
  const equityScales = useMemo(() => {
    if (!validation.isValid || filteredSeries.length < 2) return null;
    return calculateEquityScales({
      series: filteredSeries,
      width,
      height: equityHeight + margin.top + 10,
      margin: { ...margin, bottom: 10 },
    });
  }, [validation.isValid, filteredSeries, width, equityHeight, margin]);

  // Scales for Drawdown Pane
  const drawdownScales = useMemo(() => {
    if (!validation.isValid || filteredSeries.length < 2) return null;

    const topY = margin.top + equityHeight + gap;
    const plotH = drawdownHeight;
    const maxDd = Math.max(validation.maxDrawdownPct || 10, 5); // at least 5% range

    const stepX = filteredSeries.length > 1 ? chartWidth / (filteredSeries.length - 1) : chartWidth;
    const getX = (idx) => margin.left + idx * stepX;
    // Inverted: 0% is at top of pane, -maxDd is at bottom
    const getY = (dd) => topY + (Math.abs(dd) / maxDd) * plotH;

    const points = filteredSeries.map((d, i) => `${getX(i).toFixed(1)},${getY(d.drawdown_pct).toFixed(1)}`);
    const linePath = `M ${points.join(' L ')}`;
    const areaPath = `M ${getX(0).toFixed(1)},${topY} L ${points.join(' L ')} L ${getX(filteredSeries.length - 1).toFixed(1)},${topY} Z`;

    return {
      topY,
      plotH,
      maxDd,
      getX,
      getY,
      linePath,
      areaPath,
    };
  }, [validation.isValid, validation.maxDrawdownPct, filteredSeries, equityHeight, gap, drawdownHeight, margin, chartWidth]);

  // Pointer move handler for interactive crosshair
  const handlePointerMove = useCallback((e) => {
    if (!containerRef.current || filteredSeries.length < 2) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const relX = (clientX / rect.width) * width;

    if (relX < margin.left || relX > width - margin.right) {
      setHoveredIdx(null);
      return;
    }

    const plotX = relX - margin.left;
    const stepX = chartWidth / (filteredSeries.length - 1);
    const index = Math.round(plotX / stepX);
    const clampedIndex = Math.min(Math.max(index, 0), filteredSeries.length - 1);
    setHoveredIdx(clampedIndex);
  }, [filteredSeries, width, margin, chartWidth]);

  const handlePointerLeave = useCallback(() => {
    setHoveredIdx(null);
  }, []);

  // Active point for tooltip (either hovered or the latest point)
  const activeIndex = hoveredIdx != null ? hoveredIdx : (filteredSeries.length > 0 ? filteredSeries.length - 1 : null);
  const activePoint = activeIndex != null ? filteredSeries[activeIndex] : null;

  // If no valid equity series exists
  if (!validation.isValid) {
    return (
      <div className={`bg-surface rounded-2xl border border-border-primary p-6 sm:p-8 text-center space-y-4 shadow-sm ${className}`}>
        <div className="w-12 h-12 rounded-2xl bg-surface-secondary border border-border-primary flex items-center justify-center mx-auto text-tx-muted">
          <AlertCircle className="w-6 h-6" />
        </div>
        <div>
          <h3 className="font-heading font-bold text-base sm:text-lg text-tx-primary">
            Historical Equity Series Unavailable
          </h3>
          <p className="text-xs text-tx-secondary mt-1 max-w-md mx-auto">
            Periodic equity curve data was not logged for this specific backtest run. Summary metrics (Win Rate, Total Return, Max Drawdown) are computed from the closed trade records.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-surface rounded-2xl border border-border-primary p-4 sm:p-6 shadow-sm space-y-4 transition-colors ${className}`}>
      {/* Header with Title, Mode Switcher, and Range Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-primary/60 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-heading font-bold text-base sm:text-lg text-tx-primary tracking-tight">
              {title}
            </h3>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-accent-green/10 text-accent-green">
              {validation.totalReturnPct != null ? formatPercent(validation.totalReturnPct) : '—'}
            </span>
          </div>
          <p className="text-xs text-tx-secondary mt-0.5">
            Simulated portfolio capitalization: {formatCurrency(validation.startEquity, { decimals: 0 })} → {formatCurrency(validation.endEquity, { decimals: 0 })}
          </p>
        </div>

        {/* View Mode & Time Range Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* View Mode Toggle */}
          <div className="inline-flex items-center p-0.5 bg-surface-secondary border border-border-primary rounded-xl text-xs font-medium">
            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                viewMode === 'split' ? 'bg-surface text-tx-primary shadow-xs font-semibold' : 'text-tx-secondary hover:text-tx-primary'
              }`}
            >
              Split View
            </button>
            <button
              type="button"
              onClick={() => setViewMode('equity')}
              className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                viewMode === 'equity' ? 'bg-surface text-tx-primary shadow-xs font-semibold' : 'text-tx-secondary hover:text-tx-primary'
              }`}
            >
              Equity Only
            </button>
            <button
              type="button"
              onClick={() => setViewMode('drawdown')}
              className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                viewMode === 'drawdown' ? 'bg-surface text-tx-primary shadow-xs font-semibold' : 'text-tx-secondary hover:text-tx-primary'
              }`}
            >
              Drawdown
            </button>
          </div>

          {/* Time Range Selector */}
          {validation.cleanSeries.length > 5 && (
            <div className="inline-flex items-center p-0.5 bg-surface-secondary border border-border-primary rounded-xl text-xs font-medium">
              {['ALL', '1Y', '6M', '3M'].map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRange(r)}
                  className={`px-2 py-1 rounded-lg transition-all cursor-pointer ${
                    range === r ? 'bg-surface text-accent-green font-bold shadow-xs' : 'text-tx-secondary hover:text-tx-primary'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Active Inspector Banner */}
      {activePoint && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 rounded-xl bg-surface-secondary/60 border border-border-primary/60 text-xs font-mono">
          <div className="flex items-center gap-2 text-tx-secondary">
            <Calendar className="w-3.5 h-3.5 text-tx-muted" />
            <span>Date: <strong className="text-tx-primary">{activePoint.date}</strong></span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-accent-green" />
              <span>Equity: <strong className="text-tx-primary">{formatCurrency(activePoint.equity, { decimals: 0 })}</strong></span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-accent-red" />
              <span>Drawdown: <strong className={activePoint.drawdown_pct > 0 ? 'text-accent-red' : 'text-tx-secondary'}>
                {activePoint.drawdown_pct > 0 ? `-${activePoint.drawdown_pct.toFixed(2)}%` : '0.00%'}
              </strong></span>
            </div>
          </div>
        </div>
      )}

      {/* SVG Chart Pane */}
      <div
        ref={containerRef}
        onPointerMove={handlePointerMove}
        onPointerLeave={handlePointerLeave}
        className="w-full relative touch-none cursor-crosshair select-none"
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible"
          role="img"
          aria-label="Portfolio equity curve and drawdown chart"
        >
          <defs>
            {/* Equity Area Gradient */}
            <linearGradient id="equity-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
            </linearGradient>

            {/* Drawdown Area Gradient */}
            <linearGradient id="drawdown-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#EF4444" stopOpacity="0.0" />
              <stop offset="100%" stopColor="#EF4444" stopOpacity="0.25" />
            </linearGradient>
          </defs>

          {/* 1. EQUITY PANE */}
          {equityScales && (viewMode === 'split' || viewMode === 'equity') && (
            <g id="equity-pane">
              {/* Horizontal Grid lines and Y-axis ticks */}
              {equityScales.yTicks.map((tick, i) => (
                <g key={i}>
                  <line
                    x1={margin.left}
                    y1={tick.y}
                    x2={width - margin.right}
                    y2={tick.y}
                    stroke="currentColor"
                    className="text-border-primary/50"
                    strokeDasharray="3 3"
                    strokeWidth="1"
                  />
                  <text
                    x={width - margin.right + 6}
                    y={tick.y + 4}
                    fill="currentColor"
                    className="text-[10px] font-mono fill-tx-muted"
                  >
                    {formatCurrency(tick.value, { decimals: 0, compact: true })}
                  </text>
                </g>
              ))}

              {/* Area fill */}
              <path
                d={equityScales.areaPath}
                fill="url(#equity-gradient)"
              />

              {/* Equity Line */}
              <path
                d={equityScales.linePath}
                fill="none"
                stroke="#10B981"
                strokeWidth="2.25"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Starting baseline reference line */}
              <line
                x1={margin.left}
                y1={equityScales.getY(validation.startEquity)}
                x2={width - margin.right}
                y2={equityScales.getY(validation.startEquity)}
                stroke="#10B981"
                strokeOpacity="0.3"
                strokeDasharray="4 4"
                strokeWidth="1"
              />
            </g>
          )}

          {/* 2. DRAWDOWN PANE */}
          {drawdownScales && (viewMode === 'split' || viewMode === 'drawdown') && (
            <g id="drawdown-pane">
              {/* Zero baseline */}
              <line
                x1={margin.left}
                y1={drawdownScales.topY}
                x2={width - margin.right}
                y2={drawdownScales.topY}
                stroke="currentColor"
                className="text-border-primary"
                strokeWidth="1"
              />
              <text
                x={width - margin.right + 6}
                y={drawdownScales.topY + 3}
                fill="currentColor"
                className="text-[10px] font-mono fill-tx-muted"
              >
                0.0%
              </text>

              {/* Max drawdown reference line */}
              <line
                x1={margin.left}
                y1={drawdownScales.topY + drawdownScales.plotH}
                x2={width - margin.right}
                y2={drawdownScales.topY + drawdownScales.plotH}
                stroke="#EF4444"
                strokeOpacity="0.35"
                strokeDasharray="3 3"
                strokeWidth="1"
              />
              <text
                x={width - margin.right + 6}
                y={drawdownScales.topY + drawdownScales.plotH + 3}
                fill="#EF4444"
                className="text-[10px] font-mono font-semibold"
              >
                -{drawdownScales.maxDd.toFixed(1)}%
              </text>

              {/* Drawdown area */}
              <path
                d={drawdownScales.areaPath}
                fill="url(#drawdown-gradient)"
              />

              {/* Drawdown line */}
              <path
                d={drawdownScales.linePath}
                fill="none"
                stroke="#EF4444"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </g>
          )}

          {/* 3. X-AXIS DATE LABELS */}
          {filteredSeries.map((d, i) => {
            // Label every 2nd or 3rd point depending on count
            const interval = filteredSeries.length > 8 ? 2 : 1;
            if (i % interval !== 0 && i !== filteredSeries.length - 1) return null;
            const x = margin.left + (i * chartWidth) / (filteredSeries.length - 1);
            return (
              <text
                key={d.date}
                x={x}
                y={height - 8}
                textAnchor="middle"
                fill="currentColor"
                className="text-[10px] font-mono fill-tx-muted"
              >
                {d.date.slice(5)}
              </text>
            );
          })}

          {/* 4. ACTIVE HOVER CROSSHAIR & DOTS */}
          {activePoint && activeIndex != null && (
            <g id="hover-overlay" pointerEvents="none">
              {/* Vertical Crosshair Line */}
              <line
                x1={margin.left + (activeIndex * chartWidth) / (filteredSeries.length - 1)}
                y1={margin.top}
                x2={margin.left + (activeIndex * chartWidth) / (filteredSeries.length - 1)}
                y2={height - margin.bottom + 5}
                stroke="currentColor"
                className="text-accent-green"
                strokeDasharray="2 2"
                strokeWidth="1.25"
              />

              {/* Equity Point Dot */}
              {equityScales && (viewMode === 'split' || viewMode === 'equity') && (
                <circle
                  cx={margin.left + (activeIndex * chartWidth) / (filteredSeries.length - 1)}
                  cy={equityScales.getY(activePoint.equity)}
                  r="4.5"
                  className="fill-accent-green stroke-surface"
                  strokeWidth="2"
                />
              )}

              {/* Drawdown Point Dot */}
              {drawdownScales && (viewMode === 'split' || viewMode === 'drawdown') && (
                <circle
                  cx={margin.left + (activeIndex * chartWidth) / (filteredSeries.length - 1)}
                  cy={drawdownScales.getY(activePoint.drawdown_pct)}
                  r="4"
                  className="fill-accent-red stroke-surface"
                  strokeWidth="2"
                />
              )}
            </g>
          )}
        </svg>
      </div>
    </div>
  );
}
