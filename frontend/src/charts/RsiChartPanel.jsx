import React, { useMemo } from 'react';
import { Info, X, Activity } from 'lucide-react';
import { getRsiZone } from '../utils/technicalIndicators';

/**
 * RsiChartPanel
 * 
 * Synchronized sub-panel for the Relative Strength Index (RSI 14).
 * - Standard 14-period calculation
 * - Distinct 30 and 70 reference levels with neutral band shading (30-70)
 * - Clear distinction of Oversold, Neutral, and Overbought conditions
 * - Educational non-guarantee notice
 * - Interactive hover tracking synchronized with main chart
 * - Safe fallback for insufficient historical data
 */
const RsiChartPanel = ({
  data = [],
  rsiValues = [],
  containerWidth = 800,
  margin = { left: 14, right: 65, top: 12, bottom: 20 },
  hoveredIndex = null,
  onPointerMove = null,
  onPointerLeave = null,
  onClose = null,
  className = '',
}) => {
  const height = 135;
  const chartWidth = Math.max(containerWidth - margin.left - margin.right, 50);
  const plotHeight = Math.max(height - margin.top - margin.bottom, 40);

  // Check if we have sufficient valid RSI values
  const validRsiCount = useMemo(() => {
    return rsiValues.filter((v) => v !== null && !isNaN(v)).length;
  }, [rsiValues]);

  // Y coordinate calculation for RSI (0 to 100 fixed scale)
  const getYForRsi = React.useCallback(
    (val) => {
      if (val == null || isNaN(val)) return margin.top + plotHeight / 2;
      const clamped = Math.min(Math.max(Number(val), 0), 100);
      // Inverted SVG: 100 is at top, 0 is at bottom
      return margin.top + (1 - clamped / 100) * plotHeight;
    },
    [margin.top, plotHeight]
  );

  // X coordinate calculation per data index
  const candleCount = data.length;
  const stepX = candleCount > 1 ? chartWidth / (candleCount - 1) : chartWidth;
  const getXForIndex = React.useCallback(
    (index) => {
      if (candleCount <= 1) return margin.left + chartWidth / 2;
      return margin.left + index * stepX;
    },
    [candleCount, margin.left, chartWidth, stepX]
  );

  // Current active value (hovered candle or latest candle)
  const activeIndex = hoveredIndex != null ? hoveredIndex : candleCount - 1;
  const activeRsi = rsiValues[activeIndex] ?? null;
  const zoneInfo = getRsiZone(activeRsi);

  // SVG Line path for RSI
  const rsiPathD = useMemo(() => {
    if (validRsiCount === 0 || candleCount === 0) return '';
    let d = '';
    let isDrawing = false;

    for (let i = 0; i < candleCount; i++) {
      const val = rsiValues[i];
      if (val === null || isNaN(val)) {
        isDrawing = false;
        continue;
      }
      const x = getXForIndex(i);
      const y = getYForRsi(val);

      if (!isDrawing) {
        d += `M ${x} ${y}`;
        isDrawing = true;
      } else {
        d += ` L ${x} ${y}`;
      }
    }
    return d;
  }, [rsiValues, candleCount, validRsiCount, getXForIndex, getYForRsi]);

  const y70 = getYForRsi(70);
  const y50 = getYForRsi(50);
  const y30 = getYForRsi(30);

  // Insufficient history state
  if (validRsiCount === 0) {
    return (
      <div className={`mt-4 pt-3 border-t border-border-primary/80 ${className}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-heading font-semibold text-xs text-tx-primary tracking-wide flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-accent-teal" />
              RSI (14) Momentum
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-surface-secondary text-tx-muted border border-border-primary">
              Standard 14-period
            </span>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-tx-muted hover:text-tx-primary p-1 rounded hover:bg-surface-secondary cursor-pointer"
              title="Close RSI panel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        <div className="py-6 px-4 bg-surface-secondary/40 rounded-xl border border-border-primary/60 text-center">
          <p className="text-xs text-tx-secondary font-medium">
            Insufficient historical data to compute 14-period RSI.
          </p>
          <p className="text-[11px] text-tx-muted mt-1">
            Standard RSI requires at least 15 consecutive trading days of closing prices.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`mt-4 pt-3 border-t border-border-primary/80 ${className}`}>
      {/* Header bar: Title, Current Value, Zone Badge, Disclaimer Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className="font-heading font-semibold text-xs sm:text-sm text-tx-primary tracking-wide flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-accent-teal" />
            RSI (14)
          </span>

          {/* Value Display */}
          <div className="flex items-baseline gap-1.5 font-mono text-xs">
            <span className="text-tx-muted text-[11px] font-sans">
              {hoveredIndex != null ? 'Hovered:' : 'Latest:'}
            </span>
            <span className="font-bold text-tx-primary text-sm">
              {activeRsi !== null ? activeRsi.toFixed(2) : '—'}
            </span>
          </div>

          {/* Range Zone Badge */}
          <span className={`text-[10px] sm:text-xs font-semibold px-2 py-0.5 rounded-md border ${zoneInfo.badgeClass}`}>
            {zoneInfo.label}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Subtle Educational Tooltip Pill */}
          <div
            className="hidden md:flex items-center gap-1 text-[10px] text-tx-muted px-2 py-0.5 rounded bg-surface-secondary/80 border border-border-primary"
            title="RSI indicates momentum velocity. Overbought or oversold conditions do not constitute guaranteed buy/sell signals."
          >
            <Info className="w-3 h-3 text-accent-teal shrink-0" />
            <span>Descriptive indicator • Not guaranteed signals</span>
          </div>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-tx-muted hover:text-tx-primary p-1 rounded hover:bg-surface-secondary transition-colors cursor-pointer"
              title="Close RSI panel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Interactive SVG Canvas */}
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
          {/* Shaded Neutral Zone (30 to 70) */}
          <rect
            x={margin.left}
            y={y70}
            width={chartWidth}
            height={Math.max(y30 - y70, 0)}
            fill="var(--accent-primary, #14B8A6)"
            opacity="0.05"
          />

          {/* Horizontal Level: 70 (Overbought boundary) */}
          <line
            x1={margin.left}
            y1={y70}
            x2={containerWidth - margin.right}
            y2={y70}
            stroke="var(--color-accent-orange, #FF6B00)"
            strokeDasharray="3 3"
            strokeWidth="1"
            opacity="0.5"
          />
          <text
            x={containerWidth - margin.right + 6}
            y={y70 + 3.5}
            className="fill-accent-orange font-mono text-[10px] font-semibold"
            textAnchor="start"
          >
            70
          </text>

          {/* Horizontal Level: 50 (Centerline) */}
          <line
            x1={margin.left}
            y1={y50}
            x2={containerWidth - margin.right}
            y2={y50}
            stroke="currentColor"
            strokeDasharray="2 3"
            strokeWidth="0.8"
            className="text-border-primary"
            opacity="0.4"
          />
          <text
            x={containerWidth - margin.right + 6}
            y={y50 + 3.5}
            className="fill-tx-muted font-mono text-[9px]"
            textAnchor="start"
          >
            50
          </text>

          {/* Horizontal Level: 30 (Oversold boundary) */}
          <line
            x1={margin.left}
            y1={y30}
            x2={containerWidth - margin.right}
            y2={y30}
            stroke="var(--accent-primary, #14B8A6)"
            strokeDasharray="3 3"
            strokeWidth="1"
            opacity="0.5"
          />
          <text
            x={containerWidth - margin.right + 6}
            y={y30 + 3.5}
            className="fill-accent-teal font-mono text-[10px] font-semibold"
            textAnchor="start"
          >
            30
          </text>

          {/* RSI Curve Line */}
          {rsiPathD && (
            <path
              d={rsiPathD}
              fill="none"
              stroke="var(--accent-primary, #14B8A6)"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Hover Crosshair Alignment */}
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

              {/* Point Indicator on the RSI curve */}
              {activeRsi != null && (
                <>
                  <circle
                    cx={getXForIndex(hoveredIndex)}
                    cy={getYForRsi(activeRsi)}
                    r="4"
                    className="fill-accent-teal stroke-surface"
                    strokeWidth="2"
                  />
                  {/* Axis Value Pill */}
                  <g>
                    <rect
                      x={containerWidth - margin.right + 2}
                      y={getYForRsi(activeRsi) - 8}
                      width={margin.right - 4}
                      height="16"
                      rx="3"
                      className="fill-accent-teal"
                    />
                    <text
                      x={containerWidth - margin.right + 6}
                      y={getYForRsi(activeRsi) + 3.5}
                      className="fill-white font-mono text-[9px] font-bold"
                    >
                      {activeRsi.toFixed(1)}
                    </text>
                  </g>
                </>
              )}
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};

export default RsiChartPanel;
