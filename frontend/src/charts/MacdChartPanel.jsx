import React, { useMemo } from 'react';
import { Info, X, TrendingUp, TrendingDown } from 'lucide-react';
import { getMacdStatus } from '../utils/technicalIndicators';

/**
 * MacdChartPanel
 * 
 * Synchronized sub-panel for Moving Average Convergence Divergence (MACD 12, 26, 9).
 * - Fast EMA 12, Slow EMA 26, Signal 9
 * - MACD Line (Teal/Cyan) and Signal Line (Orange/Amber)
 * - MACD Histogram bars (Green for >= 0, Red for < 0)
 * - Zero center baseline with coordinate scaling
 * - Latest and hovered indicator values
 * - Safe handling of insufficient historical data
 */
const MacdChartPanel = ({
  data = [],
  macdData = [], // Array of { macd, signal, histogram }
  containerWidth = 800,
  margin = { left: 14, right: 65, top: 12, bottom: 20 },
  hoveredIndex = null,
  onPointerMove = null,
  onPointerLeave = null,
  onClose = null,
  className = '',
}) => {
  const height = 150;
  const chartWidth = Math.max(containerWidth - margin.left - margin.right, 50);
  const plotHeight = Math.max(height - margin.top - margin.bottom, 40);

  // Check valid counts
  const validMacdCount = useMemo(() => {
    return macdData.filter((d) => d && d.macd !== null).length;
  }, [macdData]);

  const candleCount = data.length;
  const stepX = candleCount > 1 ? chartWidth / (candleCount - 1) : chartWidth;
  const barWidth = Math.max(Math.min(stepX * 0.72, 10), 1.5);

  // Determine min and max across all visible MACD, Signal, and Histogram values
  const { minVal, maxVal } = useMemo(() => {
    let min = 0;
    let max = 0;

    for (let i = 0; i < candleCount; i++) {
      const item = macdData[i];
      if (!item) continue;
      if (item.macd !== null && !isNaN(item.macd)) {
        if (item.macd < min) min = item.macd;
        if (item.macd > max) max = item.macd;
      }
      if (item.signal !== null && !isNaN(item.signal)) {
        if (item.signal < min) min = item.signal;
        if (item.signal > max) max = item.signal;
      }
      if (item.histogram !== null && !isNaN(item.histogram)) {
        if (item.histogram < min) min = item.histogram;
        if (item.histogram > max) max = item.histogram;
      }
    }

    // Ensure zero is centered or well-bounded with symmetric buffer
    const absMax = Math.max(Math.abs(min), Math.abs(max), 1);
    const padded = absMax * 1.15;
    return { minVal: -padded, maxVal: padded };
  }, [macdData, candleCount]);

  const valRange = maxVal - minVal || 1;

  // Y coordinate calculation
  const getYForValue = React.useCallback(
    (val) => {
      if (val == null || isNaN(val)) return margin.top + plotHeight / 2;
      const norm = (Number(val) - minVal) / valRange;
      return margin.top + (1 - norm) * plotHeight;
    },
    [margin.top, plotHeight, minVal, valRange]
  );

  const getXForIndex = React.useCallback(
    (index) => {
      if (candleCount <= 1) return margin.left + chartWidth / 2;
      return margin.left + index * stepX;
    },
    [candleCount, margin.left, chartWidth, stepX]
  );

  const zeroY = getYForValue(0);

  // Active item
  const activeIndex = hoveredIndex != null ? hoveredIndex : candleCount - 1;
  const activeItem = macdData[activeIndex] || { macd: null, signal: null, histogram: null };
  const macdStatus = getMacdStatus(activeItem.macd, activeItem.signal, activeItem.histogram);

  // SVG Line paths for MACD and Signal
  const { macdPathD, signalPathD } = useMemo(() => {
    if (validMacdCount === 0 || candleCount === 0) {
      return { macdPathD: '', signalPathD: '' };
    }

    let mPath = '';
    let mDrawing = false;

    let sPath = '';
    let sDrawing = false;

    for (let i = 0; i < candleCount; i++) {
      const item = macdData[i];
      if (!item) continue;
      const x = getXForIndex(i);

      // MACD Line
      if (item.macd !== null && !isNaN(item.macd)) {
        const y = getYForValue(item.macd);
        if (!mDrawing) {
          mPath += `M ${x} ${y}`;
          mDrawing = true;
        } else {
          mPath += ` L ${x} ${y}`;
        }
      } else {
        mDrawing = false;
      }

      // Signal Line
      if (item.signal !== null && !isNaN(item.signal)) {
        const y = getYForValue(item.signal);
        if (!sDrawing) {
          sPath += `M ${x} ${y}`;
          sDrawing = true;
        } else {
          sPath += ` L ${x} ${y}`;
        }
      } else {
        sDrawing = false;
      }
    }

    return { macdPathD: mPath, signalPathD: sPath };
  }, [macdData, candleCount, validMacdCount, getXForIndex, getYForValue]);

  // Insufficient history state
  if (validMacdCount === 0) {
    return (
      <div className={`mt-4 pt-3 border-t border-border-primary/80 ${className}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-heading font-semibold text-xs text-tx-primary tracking-wide">
              MACD (12, 26, 9)
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-surface-secondary text-tx-muted border border-border-primary">
              Moving Average Convergence Divergence
            </span>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-tx-muted hover:text-tx-primary p-1 rounded hover:bg-surface-secondary cursor-pointer"
              title="Close MACD panel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        <div className="py-6 px-4 bg-surface-secondary/40 rounded-xl border border-border-primary/60 text-center">
          <p className="text-xs text-tx-secondary font-medium">
            Insufficient historical data to compute MACD (12, 26, 9).
          </p>
          <p className="text-[11px] text-tx-muted mt-1">
            Requires at least 34 trading days (26-period slow EMA + 9-period signal line smoothing).
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`mt-4 pt-3 border-t border-border-primary/80 ${className}`}>
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-heading font-semibold text-xs sm:text-sm text-tx-primary tracking-wide">
            MACD (12, 26, 9)
          </span>

          {/* Metric Values */}
          <div className="flex items-center gap-3 font-mono text-xs">
            {/* MACD Line Value */}
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-0.5 bg-[#38BDF8] rounded-full"></span>
              <span className="text-tx-muted text-[11px] font-sans">MACD:</span>
              <span className="font-bold text-tx-primary">
                {activeItem.macd !== null ? activeItem.macd.toFixed(2) : '—'}
              </span>
            </div>

            {/* Signal Line Value */}
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-0.5 bg-[#F97316] rounded-full"></span>
              <span className="text-tx-muted text-[11px] font-sans">Signal:</span>
              <span className="font-bold text-tx-primary">
                {activeItem.signal !== null ? activeItem.signal.toFixed(2) : '—'}
              </span>
            </div>

            {/* Histogram Value */}
            <div className="flex items-center gap-1.5">
              <span className="text-tx-muted text-[11px] font-sans">Hist:</span>
              <span
                className={`font-bold ${
                  activeItem.histogram != null && activeItem.histogram >= 0
                    ? 'text-accent-green'
                    : 'text-accent-red'
                }`}
              >
                {activeItem.histogram !== null ? (activeItem.histogram >= 0 ? '+' : '') + activeItem.histogram.toFixed(2) : '—'}
              </span>
            </div>
          </div>

          {/* Status Badge */}
          {macdStatus.status !== 'INSUFFICIENT' && (
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border flex items-center gap-1 ${macdStatus.badgeClass}`}>
              {macdStatus.histPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {macdStatus.label}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div
            className="hidden md:flex items-center gap-1 text-[10px] text-tx-muted px-2 py-0.5 rounded bg-surface-secondary/80 border border-border-primary"
            title="MACD measures trend velocity and directional momentum. It does not predict future price targets."
          >
            <Info className="w-3 h-3 text-accent-teal shrink-0" />
            <span>Trend momentum indicator</span>
          </div>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-tx-muted hover:text-tx-primary p-1 rounded hover:bg-surface-secondary transition-colors cursor-pointer"
              title="Close MACD panel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* SVG Canvas */}
      <div
        className="relative select-none cursor-crosshair overflow-hidden touch-none"
        onMouseMove={onPointerMove}
        onMouseLeave={onPointerLeave}
        onTouchStart={onPointerMove}
        onTouchMove={onPointerMove}
        onTouchEnd={onPointerLeave}
      >
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 ${containerWidth} ${height}`}
          className="overflow-visible"
        >
          {/* Zero Centerline */}
          <line
            x1={margin.left}
            y1={zeroY}
            x2={containerWidth - margin.right}
            y2={zeroY}
            stroke="currentColor"
            strokeWidth="1"
            className="text-border-primary"
            opacity="0.6"
          />
          <text
            x={containerWidth - margin.right + 6}
            y={zeroY + 3.5}
            className="fill-tx-muted font-mono text-[9px]"
            textAnchor="start"
          >
            0.0
          </text>

          {/* Upper Reference Tick */}
          <text
            x={containerWidth - margin.right + 6}
            y={margin.top + 8}
            className="fill-tx-muted font-mono text-[8px]"
            textAnchor="start"
          >
            +{maxVal.toFixed(0)}
          </text>

          {/* Lower Reference Tick */}
          <text
            x={containerWidth - margin.right + 6}
            y={margin.top + plotHeight - 2}
            className="fill-tx-muted font-mono text-[8px]"
            textAnchor="start"
          >
            {minVal.toFixed(0)}
          </text>

          {/* MACD Histogram Bars */}
          <g className="macd-histogram" opacity="0.8">
            {macdData.map((item, idx) => {
              if (!item || item.histogram == null || isNaN(item.histogram)) return null;
              const x = getXForIndex(idx);
              const histY = getYForValue(item.histogram);
              const isPositive = item.histogram >= 0;

              const top = isPositive ? histY : zeroY;
              const barHeight = Math.max(Math.abs(histY - zeroY), 1);

              return (
                <rect
                  key={`macd-bar-${idx}`}
                  x={x - barWidth / 2}
                  y={top}
                  width={barWidth}
                  height={barHeight}
                  rx="0.5"
                  className={isPositive ? 'fill-accent-green' : 'fill-accent-red'}
                  opacity={hoveredIndex === idx ? '1' : '0.65'}
                />
              );
            })}
          </g>

          {/* MACD Line (Cyan / Sky) */}
          {macdPathD && (
            <path
              d={macdPathD}
              fill="none"
              stroke="#38BDF8"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Signal Line (Orange / Amber) */}
          {signalPathD && (
            <path
              d={signalPathD}
              fill="none"
              stroke="#F97316"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Hover Crosshairs Alignment */}
          {hoveredIndex != null && hoveredIndex >= 0 && hoveredIndex < candleCount && (
            <g className="pointer-events-none">
              {/* Vertical Time Hairline */}
              <line
                x1={getXForIndex(hoveredIndex)}
                y1={margin.top}
                x2={getXForIndex(hoveredIndex)}
                y2={margin.top + plotHeight}
                stroke="var(--accent-primary, #14B8A6)"
                strokeDasharray="2 2"
                strokeWidth="1"
                opacity="0.75"
              />

              {/* Point on MACD line */}
              {activeItem.macd != null && (
                <circle
                  cx={getXForIndex(hoveredIndex)}
                  cy={getYForValue(activeItem.macd)}
                  r="3.5"
                  fill="#38BDF8"
                  className="stroke-surface"
                  strokeWidth="1.5"
                />
              )}

              {/* Point on Signal line */}
              {activeItem.signal != null && (
                <circle
                  cx={getXForIndex(hoveredIndex)}
                  cy={getYForValue(activeItem.signal)}
                  r="3"
                  fill="#F97316"
                  className="stroke-surface"
                  strokeWidth="1.5"
                />
              )}
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};

export default MacdChartPanel;
