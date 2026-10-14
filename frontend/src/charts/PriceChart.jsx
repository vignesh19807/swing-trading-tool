import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import {
  TrendingUp,
  BarChart2,
  Layers,
  Info,
} from 'lucide-react';
import {
  TIME_RANGES,
  isRangeSupported,
  filterHistoryByRange,
  validateOHLC,
  calculateScales,
  formatXAxisDate,
  formatTooltipDate,
} from '../utils/chartHelpers';
import { formatCurrency, formatPercent } from '../utils/formatters';
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents';

/**
 * PriceChart
 * 
 * Interactive Stock Price Chart implementing Phase 14 requirements:
 * - Candlestick chart when valid OHLC data is available
 * - Line chart fallback (or user-selectable toggle)
 * - 1W, 1M, 3M, 6M, 1Y time-range selector with data-length validation
 * - Synchronized trading volume sub-panel
 * - Interactive hover/touch crosshair and comprehensive price tooltip
 * - Indian Rupee (₹) price formatting
 * - Responsive sizing with ResizeObserver
 * - Native Light & Dark theme support via CSS tokens
 * - Optional Phase 13 setup levels overlay (Target, Entry, Stop Loss)
 */
const PriceChart = ({
  symbol = 'TCS',
  data = [],
  loading = false,
  error = null,
  onRetry = null,
  setupLevels = null,
  className = '',
}) => {
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(800);
  const chartHeight = 420;

  // Track responsive container width
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          setContainerWidth(Math.floor(entry.contentRect.width));
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Validate OHLC capabilities
  const validation = useMemo(() => validateOHLC(data), [data]);

  // Preferred chart type: 'candle' | 'line'
  // Auto-lock to 'line' if OHLC is missing
  const [userChartType, setUserChartType] = useState('candle');
  const activeChartType = validation.hasOHLC ? userChartType : 'line';

  // Base user-selected range
  const [selectedRange, setSelectedRange] = useState('3M');

  // Derive effective range (ensures range is strictly supported by available data without cascading renders)
  const effectiveRange = useMemo(() => {
    if (!data || data.length === 0) return selectedRange;
    if (isRangeSupported(data, selectedRange)) return selectedRange;
    if (isRangeSupported(data, '3M')) return '3M';
    if (isRangeSupported(data, '1M')) return '1M';
    return '1W';
  }, [data, selectedRange]);

  // Toggle for Phase 13 setup levels overlay
  const [showSetupLevels, setShowSetupLevels] = useState(true);

  // Hover state (index of candle currently hovered, or null)
  const [hoveredIndex, setHoveredIndex] = useState(null);

  // Filter data for effective range
  const filteredData = useMemo(() => {
    return filterHistoryByRange(data, effectiveRange);
  }, [data, effectiveRange]);

  // Coordinate scales and calculations
  const scales = useMemo(() => {
    if (!filteredData || filteredData.length === 0) return null;
    return calculateScales({
      data: filteredData,
      width: containerWidth,
      height: chartHeight,
      margin: {
        top: 24,
        right: Math.min(Math.max(Math.floor(containerWidth * 0.12), 65), 85),
        bottom: 34,
        left: 14,
      },
      setupLevels: showSetupLevels ? setupLevels : null,
      hasVolume: validation.hasVolume,
    });
  }, [filteredData, containerWidth, chartHeight, showSetupLevels, setupLevels, validation.hasVolume]);

  const {
    chartWidth = 700,
    volumeBaselineY = 380,
    candleWidth = 8,
    getYForPrice = () => 0,
    getYForVolume = () => 0,
    getXForIndex = () => 0,
    priceTicks = [],
    xTickIndices = [],
  } = scales || {};

  // Build SVG path for Line Chart
  const linePathD = useMemo(() => {
    if (!scales || filteredData.length === 0) return '';
    let d = '';
    filteredData.forEach((item, idx) => {
      const x = getXForIndex(idx);
      const y = getYForPrice(Number(item.close));
      if (idx === 0) d += `M ${x} ${y}`;
      else d += ` L ${x} ${y}`;
    });
    return d;
  }, [scales, filteredData, getXForIndex, getYForPrice]);

  // Build SVG area fill path under the line
  const areaPathD = useMemo(() => {
    if (!scales || filteredData.length === 0 || !linePathD) return '';
    const firstX = getXForIndex(0);
    const lastX = getXForIndex(filteredData.length - 1);
    const bottomY = scales.volumeBaselineY;
    return `${linePathD} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;
  }, [scales, filteredData, linePathD, getXForIndex]);

  // Keyboard navigation through candles
  const handleKeyDown = useCallback((e) => {
    if (!filteredData || filteredData.length === 0) return;
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setHoveredIndex((prev) => (prev === null ? filteredData.length - 2 : Math.max(prev - 1, 0)));
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      setHoveredIndex((prev) => (prev === null ? filteredData.length - 1 : Math.min(prev + 1, filteredData.length - 1)));
    } else if (e.key === 'Escape') {
      setHoveredIndex(null);
    }
  }, [filteredData]);

  // Mouse / Touch scrubber handlers
  const handlePointerMove = (e) => {
    if (!scales || !containerRef.current || filteredData.length === 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const mouseX = clientX - rect.left;

    // Find closest index
    const candleCount = filteredData.length;
    let closestIndex = 0;
    let minDistance = Infinity;

    for (let i = 0; i < candleCount; i++) {
      const candleX = scales.getXForIndex(i);
      const dist = Math.abs(mouseX - candleX);
      if (dist < minDistance) {
        minDistance = dist;
        closestIndex = i;
      }
    }
    setHoveredIndex(closestIndex);
  };

  const handlePointerLeave = () => {
    setHoveredIndex(null);
  };

  // Currently focused item (hovered item or latest candle)
  const activeCandle = useMemo(() => {
    if (!filteredData || filteredData.length === 0) return null;
    if (hoveredIndex != null && filteredData[hoveredIndex]) {
      return { item: filteredData[hoveredIndex], isHovered: true, index: hoveredIndex };
    }
    return { item: filteredData[filteredData.length - 1], isHovered: false, index: filteredData.length - 1 };
  }, [filteredData, hoveredIndex]);

  // Compute period summary change
  const periodStats = useMemo(() => {
    if (!filteredData || filteredData.length < 2) return null;
    const firstClose = Number(filteredData[0].close);
    const lastClose = Number(filteredData[filteredData.length - 1].close);
    const diff = lastClose - firstClose;
    const pct = firstClose > 0 ? (diff / firstClose) * 100 : 0;
    return { diff, pct, isPositive: diff >= 0 };
  }, [filteredData]);

  // Loading state
  if (loading) {
    return (
      <div className={`bg-surface rounded-2xl border border-border-primary p-6 shadow-sm transition-colors ${className}`}>
        <div className="flex justify-between items-center mb-6">
          <div className="h-6 bg-surface-secondary rounded w-48 animate-pulse"></div>
          <div className="h-8 bg-surface-secondary rounded w-64 animate-pulse"></div>
        </div>
        <LoadingState message="Loading historical price chart data..." className="min-h-[350px]" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`bg-surface rounded-2xl border border-border-primary p-6 shadow-sm transition-colors ${className}`}>
        <ErrorState
          title="Price Chart Unavailable"
          message={error}
          onRetry={onRetry}
          className="min-h-[320px]"
        />
      </div>
    );
  }

  // Empty state
  if (!data || data.length === 0) {
    return (
      <div className={`bg-surface rounded-2xl border border-border-primary p-6 shadow-sm transition-colors ${className}`}>
        <EmptyState
          message={`No historical price records available for ${symbol}.`}
          className="min-h-[320px]"
        />
      </div>
    );
  }

  // Active candle price metrics
  const displayItem = activeCandle?.item;
  const itemClose = displayItem ? Number(displayItem.close) : null;
  const itemOpen = displayItem?.open != null ? Number(displayItem.open) : null;
  const itemHigh = displayItem?.high != null ? Number(displayItem.high) : null;
  const itemLow = displayItem?.low != null ? Number(displayItem.low) : null;
  const itemVolume = displayItem?.volume != null ? Number(displayItem.volume) : null;

  // Day change of the hovered candle relative to its own open
  const dayChange = (itemClose != null && itemOpen != null) ? itemClose - itemOpen : null;
  const dayChangePct = (dayChange != null && itemOpen && itemOpen > 0) ? (dayChange / itemOpen) * 100 : null;
  const isCandleGreen = dayChange != null ? dayChange >= 0 : true;

  return (
    <div
      ref={containerRef}
      className={`bg-surface rounded-2xl border border-border-primary p-5 sm:p-7 shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-accent-teal/50 ${className}`}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      role="region"
      aria-label={`Interactive price chart for ${symbol}`}
    >
      {/* Chart Top Controls & Summary Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-border-primary">
        {/* Left: Current Inspection / Title */}
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-heading font-bold text-xl sm:text-2xl text-tx-primary tracking-tight">
              {symbol} Price Action
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-surface-secondary text-tx-secondary font-medium border border-border-primary/60">
              NSE Daily (EOD)
            </span>
            {!validation.hasOHLC && (
              <span className="text-[11px] px-2 py-0.5 rounded bg-accent-warning/10 text-accent-warning font-semibold border border-accent-warning/30">
                Line Only (OHLC Unavailable)
              </span>
            )}
          </div>

          {/* Quick Metrics Bar: Open, High, Low, Close, Volume */}
          <div className="flex items-center gap-3 sm:gap-4 text-xs font-mono flex-wrap text-tx-secondary pt-0.5">
            <div>
              <span className="text-tx-muted mr-1 font-sans">Date:</span>
              <span className="font-semibold text-tx-primary">
                {displayItem ? formatXAxisDate(displayItem.date) : '—'}
              </span>
            </div>
            {itemOpen != null && (
              <div>
                <span className="text-tx-muted mr-1 font-sans">O:</span>
                <span className="font-semibold text-tx-primary">{formatCurrency(itemOpen)}</span>
              </div>
            )}
            {itemHigh != null && (
              <div>
                <span className="text-tx-muted mr-1 font-sans">H:</span>
                <span className="font-semibold text-accent-green">{formatCurrency(itemHigh)}</span>
              </div>
            )}
            {itemLow != null && (
              <div>
                <span className="text-tx-muted mr-1 font-sans">L:</span>
                <span className="font-semibold text-accent-red">{formatCurrency(itemLow)}</span>
              </div>
            )}
            <div>
              <span className="text-tx-muted mr-1 font-sans">C:</span>
              <span className="font-bold text-tx-primary">{formatCurrency(itemClose)}</span>
            </div>
            {dayChange != null && (
              <div className={`font-semibold ${isCandleGreen ? 'text-accent-green' : 'text-accent-red'}`}>
                {dayChange >= 0 ? '+' : ''}{formatCurrency(dayChange)} ({formatPercent(dayChangePct)})
              </div>
            )}
            {itemVolume != null && (
              <div className="hidden sm:inline-block">
                <span className="text-tx-muted mr-1 font-sans">Vol:</span>
                <span className="text-tx-primary font-medium">{itemVolume.toLocaleString('en-IN')}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Controls Toolbar (Time-Range Buttons & Chart Type Toggle) */}
        <div className="flex items-center gap-3 flex-wrap self-start lg:self-auto">
          {/* Chart Type Toggle: Candlestick vs Line */}
          {validation.hasOHLC && (
            <div className="inline-flex rounded-lg bg-surface-secondary p-1 border border-border-primary" role="group" aria-label="Chart type toggle">
              <button
                type="button"
                onClick={() => setUserChartType('candle')}
                aria-pressed={activeChartType === 'candle'}
                className={`p-1.5 rounded-md text-xs font-medium transition-all cursor-pointer flex items-center gap-1 ${
                  activeChartType === 'candle'
                    ? 'bg-surface text-tx-primary shadow-xs font-semibold'
                    : 'text-tx-secondary hover:text-tx-primary'
                }`}
                title="Candlestick Chart (OHLC)"
              >
                <BarChart2 className="w-3.5 h-3.5 rotate-90" />
                <span className="hidden sm:inline">Candles</span>
              </button>
              <button
                type="button"
                onClick={() => setUserChartType('line')}
                aria-pressed={activeChartType === 'line'}
                className={`p-1.5 rounded-md text-xs font-medium transition-all cursor-pointer flex items-center gap-1 ${
                  activeChartType === 'line'
                    ? 'bg-surface text-tx-primary shadow-xs font-semibold'
                    : 'text-tx-secondary hover:text-tx-primary'
                }`}
                title="Line Chart (Closing Price)"
              >
                <TrendingUp className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Line</span>
              </button>
            </div>
          )}

          {/* Time Range Selector: 1W, 1M, 3M, 6M, 1Y */}
          <div className="inline-flex rounded-lg bg-surface-secondary p-1 border border-border-primary" role="tablist" aria-label="Time range selector">
            {TIME_RANGES.map((range) => {
              const supported = isRangeSupported(data, range.key);
              const isActive = effectiveRange === range.key;

              return (
                <button
                  key={range.key}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  disabled={!supported}
                  onClick={() => setSelectedRange(range.key)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                    !supported
                      ? 'opacity-40 cursor-not-allowed text-tx-muted'
                      : isActive
                      ? 'bg-surface text-tx-primary shadow-xs font-bold'
                      : 'text-tx-secondary hover:text-tx-primary cursor-pointer'
                  }`}
                  title={supported ? `${range.description} view` : `Insufficient historical data for ${range.label}`}
                >
                  {range.label}
                </button>
              );
            })}
          </div>

          {/* Setup Levels Overlay Toggle (if setup levels provided) */}
          {setupLevels && (setupLevels.target || setupLevels.stopLoss) && (
            <button
              type="button"
              onClick={() => setShowSetupLevels((prev) => !prev)}
              aria-pressed={showSetupLevels}
              className={`p-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer flex items-center gap-1 ${
                showSetupLevels
                  ? 'border-accent-teal/40 bg-accent-teal/10 text-accent-teal font-semibold'
                  : 'border-border-primary bg-surface-secondary text-tx-secondary hover:text-tx-primary'
              }`}
              title="Toggle Trading Setup reference levels (Target, Stop-Loss, Entry)"
            >
              <Layers className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Levels</span>
            </button>
          )}
        </div>
      </div>

      {/* SVG Interactive Canvas */}
      <div
        className="relative my-4 select-none cursor-crosshair overflow-hidden touch-none"
        onMouseMove={handlePointerMove}
        onMouseLeave={handlePointerLeave}
        onTouchStart={handlePointerMove}
        onTouchMove={handlePointerMove}
        onTouchEnd={handlePointerLeave}
      >
        <svg
          width="100%"
          height={chartHeight}
          viewBox={`0 0 ${containerWidth} ${chartHeight}`}
          className="overflow-visible"
        >
          <defs>
            {/* Area gradient for line mode */}
            <linearGradient id="priceAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent-primary, #14B8A6)" stopOpacity="0.25" />
              <stop offset="100%" stopColor="var(--accent-primary, #14B8A6)" stopOpacity="0.0" />
            </linearGradient>

            {/* Clip path for chart bounds */}
            <clipPath id="chartClip">
              <rect x={scales?.margin?.left || 0} y="0" width={chartWidth || containerWidth} height={chartHeight} />
            </clipPath>
          </defs>

          {/* Background Grid Lines & Y-Axis Labels */}
          {scales && priceTicks && (
            <g className="grid-lines" opacity="0.6">
              {priceTicks.map((tick) => {
                const y = getYForPrice(tick);
                if (y < 10 || y > volumeBaselineY + 10) return null;

                return (
                  <g key={tick}>
                    <line
                      x1={scales.margin.left}
                      y1={y}
                      x2={containerWidth - scales.margin.right}
                      y2={y}
                      stroke="currentColor"
                      strokeDasharray="3 3"
                      strokeWidth="1"
                      className="text-border-primary"
                    />
                    <text
                      x={containerWidth - scales.margin.right + 8}
                      y={y + 3.5}
                      className="fill-tx-muted font-mono text-[10px]"
                      textAnchor="start"
                    >
                      {formatCurrency(tick, { decimals: 0 })}
                    </text>
                  </g>
                );
              })}
            </g>
          )}

          {/* Volume Baseline Separator */}
          {validation.hasVolume && scales && (
            <g>
              <line
                x1={scales.margin.left}
                y1={scales.volumeBaselineY - scales.volumeHeight}
                x2={containerWidth - scales.margin.right}
                y2={scales.volumeBaselineY - scales.volumeHeight}
                stroke="currentColor"
                strokeWidth="1"
                opacity="0.2"
                className="text-border-primary"
              />
              <text
                x={scales.margin.left + 4}
                y={scales.volumeBaselineY - scales.volumeHeight + 11}
                className="fill-tx-muted font-sans text-[9px] uppercase tracking-wider font-semibold"
                opacity="0.7"
              >
                Volume
              </text>
            </g>
          )}

          {/* Trading Volume Bars */}
          {validation.hasVolume && scales && (
            <g className="volume-bars" opacity="0.75">
              {filteredData.map((d, idx) => {
                const x = getXForIndex(idx);
                const volY = getYForVolume(d.volume);
                const barHeight = Math.max(scales.volumeBaselineY - volY, 1);
                const isGreen = d.open != null ? Number(d.close) >= Number(d.open) : true;
                const barWidth = Math.max(candleWidth * 0.85, 1.5);

                return (
                  <rect
                    key={`vol-${d.date}-${idx}`}
                    x={x - barWidth / 2}
                    y={volY}
                    width={barWidth}
                    height={barHeight}
                    rx="1"
                    className={isGreen ? 'fill-accent-green' : 'fill-accent-red'}
                    opacity={hoveredIndex === idx ? '1' : '0.6'}
                  />
                );
              })}
            </g>
          )}

          {/* Chart Rendering: Line Chart Mode */}
          {activeChartType === 'line' && scales && (
            <g className="line-chart">
              {/* Area gradient under line */}
              <path d={areaPathD} fill="url(#priceAreaGradient)" />

              {/* Main Line Stroke */}
              <path
                d={linePathD}
                fill="none"
                stroke="var(--accent-primary, #14B8A6)"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Data points highlight */}
              {filteredData.map((d, idx) => {
                const x = getXForIndex(idx);
                const y = getYForPrice(Number(d.close));
                const isHovered = hoveredIndex === idx;

                if (!isHovered && filteredData.length > 30) return null;

                return (
                  <circle
                    key={`dot-${idx}`}
                    cx={x}
                    cy={y}
                    r={isHovered ? 4.5 : 2}
                    className={isHovered ? 'fill-accent-teal stroke-surface' : 'fill-accent-teal'}
                    strokeWidth={isHovered ? 2 : 0}
                  />
                );
              })}
            </g>
          )}

          {/* Chart Rendering: Candlestick Chart Mode */}
          {activeChartType === 'candle' && scales && (
            <g className="candlesticks">
              {filteredData.map((d, idx) => {
                const x = getXForIndex(idx);
                const openY = getYForPrice(Number(d.open));
                const closeY = getYForPrice(Number(d.close));
                const highY = getYForPrice(Number(d.high));
                const lowY = getYForPrice(Number(d.low));

                const isGreen = Number(d.close) >= Number(d.open);
                const bodyTop = Math.min(openY, closeY);
                const bodyHeight = Math.max(Math.abs(closeY - openY), 1.5);
                const isHovered = hoveredIndex === idx;

                const colorClass = isGreen ? 'stroke-accent-green fill-accent-green' : 'stroke-accent-red fill-accent-red';

                return (
                  <g
                    key={`candle-${d.date}-${idx}`}
                    className={`transition-opacity ${hoveredIndex != null && !isHovered ? 'opacity-85' : 'opacity-100'}`}
                  >
                    {/* Wick: High to Low Line */}
                    <line
                      x1={x}
                      y1={highY}
                      x2={x}
                      y2={lowY}
                      strokeWidth={isHovered ? 1.75 : 1.2}
                      className={isGreen ? 'stroke-accent-green' : 'stroke-accent-red'}
                    />

                    {/* Candle Body */}
                    <rect
                      x={x - candleWidth / 2}
                      y={bodyTop}
                      width={candleWidth}
                      height={bodyHeight}
                      rx={candleWidth > 4 ? 1 : 0}
                      className={colorClass}
                      strokeWidth={isHovered ? 1.5 : 0.5}
                    />
                  </g>
                );
              })}
            </g>
          )}

          {/* Optional Phase 13 Setup Reference Lines */}
          {showSetupLevels && setupLevels && scales && (
            <g className="setup-reference-lines" opacity="0.9">
              {/* Target Line */}
              {setupLevels.target != null && setupLevels.target > 0 && (
                <g>
                  <line
                    x1={scales.margin.left}
                    y1={getYForPrice(setupLevels.target)}
                    x2={containerWidth - scales.margin.right}
                    y2={getYForPrice(setupLevels.target)}
                    stroke="var(--color-status-success, #16A34A)"
                    strokeDasharray="4 4"
                    strokeWidth="1.5"
                  />
                  <rect
                    x={containerWidth - scales.margin.right + 2}
                    y={getYForPrice(setupLevels.target) - 9}
                    width={scales.margin.right - 4}
                    height="18"
                    rx="3"
                    className="fill-accent-green/20"
                  />
                  <text
                    x={containerWidth - scales.margin.right + 5}
                    y={getYForPrice(setupLevels.target) + 3}
                    className="fill-accent-green font-mono text-[9px] font-bold"
                  >
                    TGT {formatCurrency(setupLevels.target, { decimals: 0 })}
                  </text>
                </g>
              )}

              {/* Entry Level Line */}
              {setupLevels.entry != null && setupLevels.entry > 0 && (
                <g>
                  <line
                    x1={scales.margin.left}
                    y1={getYForPrice(setupLevels.entry)}
                    x2={containerWidth - scales.margin.right}
                    y2={getYForPrice(setupLevels.entry)}
                    stroke="var(--accent-primary, #14B8A6)"
                    strokeDasharray="3 3"
                    strokeWidth="1.5"
                  />
                  <rect
                    x={containerWidth - scales.margin.right + 2}
                    y={getYForPrice(setupLevels.entry) - 9}
                    width={scales.margin.right - 4}
                    height="18"
                    rx="3"
                    className="fill-accent-teal/20"
                  />
                  <text
                    x={containerWidth - scales.margin.right + 5}
                    y={getYForPrice(setupLevels.entry) + 3}
                    className="fill-accent-teal font-mono text-[9px] font-bold"
                  >
                    ENT {formatCurrency(setupLevels.entry, { decimals: 0 })}
                  </text>
                </g>
              )}

              {/* Stop Loss Line */}
              {setupLevels.stopLoss != null && setupLevels.stopLoss > 0 && (
                <g>
                  <line
                    x1={scales.margin.left}
                    y1={getYForPrice(setupLevels.stopLoss)}
                    x2={containerWidth - scales.margin.right}
                    y2={getYForPrice(setupLevels.stopLoss)}
                    stroke="var(--color-status-danger, #EF4444)"
                    strokeDasharray="4 4"
                    strokeWidth="1.5"
                  />
                  <rect
                    x={containerWidth - scales.margin.right + 2}
                    y={getYForPrice(setupLevels.stopLoss) - 9}
                    width={scales.margin.right - 4}
                    height="18"
                    rx="3"
                    className="fill-accent-red/20"
                  />
                  <text
                    x={containerWidth - scales.margin.right + 5}
                    y={getYForPrice(setupLevels.stopLoss) + 3}
                    className="fill-accent-red font-mono text-[9px] font-bold"
                  >
                    STP {formatCurrency(setupLevels.stopLoss, { decimals: 0 })}
                  </text>
                </g>
              )}
            </g>
          )}

          {/* Interactive Hover Crosshairs */}
          {hoveredIndex != null && scales && (
            <g className="crosshair-overlay pointer-events-none">
              {/* Vertical Time Hairline */}
              <line
                x1={getXForIndex(hoveredIndex)}
                y1={scales.margin.top}
                x2={getXForIndex(hoveredIndex)}
                y2={scales.volumeBaselineY}
                stroke="var(--accent-primary, #14B8A6)"
                strokeDasharray="2 2"
                strokeWidth="1.2"
                opacity="0.8"
              />

              {/* Horizontal Price Hairline */}
              {itemClose != null && (
                <line
                  x1={scales.margin.left}
                  y1={getYForPrice(itemClose)}
                  x2={containerWidth - scales.margin.right}
                  y2={getYForPrice(itemClose)}
                  stroke="var(--accent-primary, #14B8A6)"
                  strokeDasharray="2 2"
                  strokeWidth="1.2"
                  opacity="0.8"
                />
              )}

              {/* Price axis pin pill */}
              {itemClose != null && (
                <g>
                  <rect
                    x={containerWidth - scales.margin.right + 1}
                    y={getYForPrice(itemClose) - 10}
                    width={scales.margin.right - 2}
                    height="20"
                    rx="3"
                    className="fill-accent-teal"
                  />
                  <text
                    x={containerWidth - scales.margin.right + 6}
                    y={getYForPrice(itemClose) + 3.5}
                    className="fill-white font-mono text-[10px] font-bold"
                  >
                    {formatCurrency(itemClose, { decimals: 0 })}
                  </text>
                </g>
              )}
            </g>
          )}

          {/* X-Axis Date Labels at Bottom */}
          {scales && xTickIndices && (
            <g className="x-axis-labels">
              {xTickIndices.map((idx) => {
                const item = filteredData[idx];
                if (!item) return null;
                const x = getXForIndex(idx);
                const y = scales.volumeBaselineY + 18;

                return (
                  <text
                    key={`x-label-${idx}`}
                    x={x}
                    y={y}
                    className="fill-tx-muted font-mono text-[10px]"
                    textAnchor="middle"
                  >
                    {formatXAxisDate(item.date)}
                  </text>
                );
              })}
            </g>
          )}
        </svg>

        {/* Hover Details Card (Floating popover tooltip) */}
        {hoveredIndex != null && displayItem && scales && (
          <div
            className="absolute top-2 left-3 bg-surface/95 backdrop-blur-md border border-border-primary rounded-xl p-3 shadow-lg pointer-events-none transition-all z-20 text-xs text-tx-secondary"
            style={{
              maxWidth: '280px',
            }}
          >
            <div className="font-semibold text-tx-primary pb-1.5 mb-1.5 border-b border-border-primary/60 flex items-center justify-between gap-4">
              <span>{formatTooltipDate(displayItem.date)}</span>
              {dayChangePct != null && (
                <span className={`font-mono text-[11px] font-bold ${isCandleGreen ? 'text-accent-green' : 'text-accent-red'}`}>
                  {formatPercent(dayChangePct)}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-[11px]">
              {displayItem.open != null && (
                <div className="flex justify-between">
                  <span className="text-tx-muted">Open:</span>
                  <span className="text-tx-primary font-medium">{formatCurrency(displayItem.open)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-tx-muted">Close:</span>
                <span className="text-tx-primary font-bold">{formatCurrency(displayItem.close)}</span>
              </div>
              {displayItem.high != null && (
                <div className="flex justify-between">
                  <span className="text-tx-muted">High:</span>
                  <span className="text-accent-green font-medium">{formatCurrency(displayItem.high)}</span>
                </div>
              )}
              {displayItem.low != null && (
                <div className="flex justify-between">
                  <span className="text-tx-muted">Low:</span>
                  <span className="text-accent-red font-medium">{formatCurrency(displayItem.low)}</span>
                </div>
              )}
              {displayItem.volume != null && (
                <div className="col-span-2 flex justify-between pt-1 border-t border-border-primary/40 text-[10px]">
                  <span className="text-tx-muted">Volume:</span>
                  <span className="text-tx-secondary font-medium">{Number(displayItem.volume).toLocaleString('en-IN')} shares</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Chart Footer: Period Summary & Simulation Notice */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-3 border-t border-border-primary text-xs text-tx-secondary">
        <div className="flex items-center gap-3">
          {periodStats && (
            <div>
              <span className="text-tx-muted">Period Change ({effectiveRange}): </span>
              <span className={`font-mono font-semibold ${periodStats.isPositive ? 'text-accent-green' : 'text-accent-red'}`}>
                {periodStats.isPositive ? '+' : ''}{formatCurrency(periodStats.diff)} ({formatPercent(periodStats.pct)})
              </span>
            </div>
          )}
          <span className="text-tx-muted hidden sm:inline">•</span>
          <div className="text-tx-muted">
            {filteredData.length} Trading Days
          </div>
        </div>

        {/* Deterministic / Mock Data Transparent Notice */}
        <div className="flex items-center gap-1.5 text-[11px] text-tx-muted">
          <Info className="w-3.5 h-3.5 text-accent-teal shrink-0" />
          <span>Simulated EOD Data (Offline / Mock Mode)</span>
        </div>
      </div>
    </div>
  );
};

export default PriceChart;
