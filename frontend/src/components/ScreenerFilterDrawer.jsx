/**
 * @file ScreenerFilterDrawer.jsx
 * @description Slide-over drawer and filter panel for technical stock screening and strategy filtering.
 * 
 * FEATURES:
 *   - Basic market criteria: Sector, Direction, Recommendation, Price Range, Price Change
 *   - Technical strategy criteria: Price vs EMA 20/50/200, RSI 14 ranges, MACD crossover, MACD Histogram
 *   - 1-click strategy presets (Bullish Momentum, Oversold Pullback, Trend Following, Bearish Pressure)
 *   - Keyboard accessible (Escape closes, proper ARIA modal roles, labelled inputs)
 *   - Result count display and Reset All action
 */

import React, { useEffect } from 'react';
import {
  X,
  SlidersHorizontal,
  RotateCcw,
  Sparkles,
  Check,
  Activity,
  Filter
} from 'lucide-react';
import {
  DEFAULT_SCREENER_FILTERS,
  SCREENER_PRESETS,
  countActiveFilters
} from '../utils/screenerFilters';

const ScreenerFilterDrawer = ({
  isOpen,
  onClose,
  filters,
  onFilterChange,
  onResetFilters,
  uniqueSectors = [],
  matchCount = 0,
  totalCount = 0,
}) => {
  // Close drawer on Escape key press
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Lock body scroll when drawer is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const activeCount = countActiveFilters(filters);

  const updateField = (key, value) => {
    onFilterChange({ ...filters, [key]: value });
  };

  const applyPreset = (preset) => {
    onFilterChange({
      ...DEFAULT_SCREENER_FILTERS,
      search: filters.search, // preserve search term
      ...preset.filters,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden"
      aria-labelledby="screener-drawer-title"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md md:max-w-lg bg-surface border-l border-border-primary shadow-2xl flex flex-col justify-between text-tx-primary transition-all">
          
          {/* 1. DRAWER HEADER */}
          <div className="p-5 border-b border-border-primary flex items-center justify-between bg-surface-secondary/50 shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-accent-green/10 text-accent-green flex items-center justify-center shrink-0">
                <SlidersHorizontal className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 id="screener-drawer-title" className="font-heading font-bold text-lg text-tx-primary">
                    Screener & Filters
                  </h2>
                  {activeCount > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-accent-green text-surface font-mono">
                      {activeCount}
                    </span>
                  )}
                </div>
                <p className="text-xs text-tx-secondary">
                  Refine stocks by fundamental metrics & technical indicators
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {activeCount > 0 && (
                <button
                  type="button"
                  onClick={onResetFilters}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-accent-red hover:bg-accent-red/10 border border-accent-red/20 transition-colors"
                  title="Reset all filters"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Reset</span>
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-xl text-tx-secondary hover:text-tx-primary hover:bg-surface-secondary border border-border-primary transition-colors cursor-pointer"
                aria-label="Close screener drawer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* 2. DRAWER BODY (SCROLLABLE) */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6">

            {/* Quick Strategy Presets */}
            <div className="space-y-2.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-tx-muted">
                <Sparkles className="w-3.5 h-3.5 text-accent-teal" />
                <span>Strategy Presets</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {SCREENER_PRESETS.map((preset) => {
                  return (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => applyPreset(preset)}
                      className="text-left p-2.5 rounded-xl border border-border-primary bg-surface-secondary/40 hover:bg-surface-secondary hover:border-accent-green/40 transition-all group cursor-pointer"
                    >
                      <div className="text-xs font-semibold text-tx-primary group-hover:text-accent-green transition-colors">
                        {preset.label}
                      </div>
                      <div className="text-[10px] text-tx-secondary mt-0.5 line-clamp-1">
                        {preset.description}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="border-t border-border-primary/50" />

            {/* SECTION A: TECHNICAL STRATEGY FILTERS */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-accent-green">
                  <Activity className="w-3.5 h-3.5" />
                  <span>Technical Strategy Criteria</span>
                </div>
                <span className="text-[10px] font-mono text-tx-muted">Daily OHLCV Indicators</span>
              </div>

              {/* Price vs Exponential Moving Averages */}
              <div className="space-y-3 p-3.5 rounded-xl bg-surface-secondary/30 border border-border-primary">
                <div className="text-xs font-medium text-tx-primary">Moving Average Alignment (EMA)</div>

                {/* EMA 20 */}
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-tx-secondary font-mono">Price vs EMA 20:</span>
                  <div className="flex items-center rounded-lg bg-surface border border-border-primary p-0.5 text-xs font-medium">
                    {['ALL', 'ABOVE', 'BELOW'].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => updateField('priceVsEma20', opt)}
                        className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                          filters.priceVsEma20 === opt
                            ? 'bg-accent-green text-surface font-semibold shadow-xs'
                            : 'text-tx-secondary hover:text-tx-primary'
                        }`}
                      >
                        {opt === 'ALL' ? 'Any' : opt === 'ABOVE' ? '> EMA 20' : '< EMA 20'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* EMA 50 */}
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-tx-secondary font-mono">Price vs EMA 50:</span>
                  <div className="flex items-center rounded-lg bg-surface border border-border-primary p-0.5 text-xs font-medium">
                    {['ALL', 'ABOVE', 'BELOW'].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => updateField('priceVsEma50', opt)}
                        className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                          filters.priceVsEma50 === opt
                            ? 'bg-accent-green text-surface font-semibold shadow-xs'
                            : 'text-tx-secondary hover:text-tx-primary'
                        }`}
                      >
                        {opt === 'ALL' ? 'Any' : opt === 'ABOVE' ? '> EMA 50' : '< EMA 50'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* EMA 200 */}
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-tx-secondary font-mono">Price vs EMA 200:</span>
                  <div className="flex items-center rounded-lg bg-surface border border-border-primary p-0.5 text-xs font-medium">
                    {['ALL', 'ABOVE', 'BELOW'].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => updateField('priceVsEma200', opt)}
                        className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                          filters.priceVsEma200 === opt
                            ? 'bg-accent-green text-surface font-semibold shadow-xs'
                            : 'text-tx-secondary hover:text-tx-primary'
                        }`}
                      >
                        {opt === 'ALL' ? 'Any' : opt === 'ABOVE' ? '> EMA 200' : '< EMA 200'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Relative Strength Index (RSI 14) */}
              <div className="space-y-2 p-3.5 rounded-xl bg-surface-secondary/30 border border-border-primary">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-tx-primary">Relative Strength Index (RSI 14)</span>
                  <span className="text-[10px] text-tx-muted font-mono">14 Period</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5 text-xs">
                  {[
                    { id: 'ALL', label: 'All RSI Levels' },
                    { id: 'OVERSOLD', label: '< 30 (Oversold)' },
                    { id: 'NEUTRAL_LOW', label: '30 – 50 (Bearish/Pullback)' },
                    { id: 'NEUTRAL_HIGH', label: '50 – 70 (Bullish Momentum)' },
                    { id: 'OVERBOUGHT', label: '> 70 (Overbought)' },
                  ].map((lvl) => (
                    <button
                      key={lvl.id}
                      type="button"
                      onClick={() => updateField('rsiRange', lvl.id)}
                      className={`p-2 rounded-lg text-left border transition-all cursor-pointer ${
                        filters.rsiRange === lvl.id
                          ? 'bg-accent-green/10 border-accent-green text-accent-green font-semibold'
                          : 'bg-surface border-border-primary text-tx-secondary hover:text-tx-primary'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{lvl.label}</span>
                        {filters.rsiRange === lvl.id && <Check className="w-3.5 h-3.5 shrink-0" />}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* MACD Indicators */}
              <div className="space-y-3 p-3.5 rounded-xl bg-surface-secondary/30 border border-border-primary">
                <div className="text-xs font-medium text-tx-primary">MACD Momentum (12, 26, 9)</div>

                {/* MACD vs Signal */}
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-tx-secondary">MACD vs Signal:</span>
                  <div className="flex items-center rounded-lg bg-surface border border-border-primary p-0.5 text-xs font-medium">
                    {[
                      { id: 'ALL', label: 'Any' },
                      { id: 'ABOVE', label: 'MACD > Signal' },
                      { id: 'BELOW', label: 'MACD < Signal' },
                    ].map((opt) => (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => updateField('macdVsSignal', opt.id)}
                        className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                          filters.macdVsSignal === opt.id
                            ? 'bg-accent-green text-surface font-semibold shadow-xs'
                            : 'text-tx-secondary hover:text-tx-primary'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* MACD Histogram */}
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-tx-secondary">MACD Histogram:</span>
                  <div className="flex items-center rounded-lg bg-surface border border-border-primary p-0.5 text-xs font-medium">
                    {[
                      { id: 'ALL', label: 'Any' },
                      { id: 'POSITIVE', label: 'Positive (> 0)' },
                      { id: 'NEGATIVE', label: 'Negative (< 0)' },
                    ].map((opt) => (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => updateField('macdHistogram', opt.id)}
                        className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                          filters.macdHistogram === opt.id
                            ? 'bg-accent-green text-surface font-semibold shadow-xs'
                            : 'text-tx-secondary hover:text-tx-primary'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-border-primary/50" />

            {/* SECTION B: MARKET & EQUITIES CRITERIA (BASIC FILTERS) */}
            <div className="space-y-4">
              <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-tx-muted">
                <Filter className="w-3.5 h-3.5" />
                <span>Market & Equities Criteria</span>
              </div>

              {/* Sector Dropdown */}
              <div className="space-y-1.5">
                <label htmlFor="screener-sector" className="block text-xs font-medium text-tx-secondary">
                  Sector
                </label>
                <select
                  id="screener-sector"
                  value={filters.sector}
                  onChange={(e) => updateField('sector', e.target.value)}
                  className="w-full px-3 py-2 bg-surface-secondary border border-border-primary rounded-xl text-xs sm:text-sm text-tx-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
                >
                  <option value="ALL">All Sectors</option>
                  {uniqueSectors.map((sec) => (
                    <option key={sec} value={sec}>{sec}</option>
                  ))}
                </select>
              </div>

              {/* Market Direction */}
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-tx-secondary">
                  Market Direction
                </label>
                <div className="grid grid-cols-4 gap-1.5 text-xs">
                  {[
                    { id: 'ALL', label: 'All' },
                    { id: 'BULLISH', label: 'Bullish' },
                    { id: 'NEUTRAL', label: 'Neutral' },
                    { id: 'BEARISH', label: 'Bearish' },
                  ].map((dir) => (
                    <button
                      key={dir.id}
                      type="button"
                      onClick={() => updateField('direction', dir.id)}
                      className={`py-1.5 px-2 rounded-lg text-center font-medium border transition-colors cursor-pointer ${
                        filters.direction === dir.id
                          ? 'bg-accent-green text-surface border-accent-green font-semibold shadow-xs'
                          : 'bg-surface-secondary border-border-primary text-tx-secondary hover:text-tx-primary'
                      }`}
                    >
                      {dir.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Recommendation / Signal */}
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-tx-secondary">
                  Signal / Recommendation
                </label>
                <div className="grid grid-cols-4 gap-1.5 text-xs">
                  {[
                    { id: 'ALL', label: 'All' },
                    { id: 'BUY', label: 'Buy' },
                    { id: 'WATCH', label: 'Watch' },
                    { id: 'SELL', label: 'Sell' },
                  ].map((rec) => (
                    <button
                      key={rec.id}
                      type="button"
                      onClick={() => updateField('recommendation', rec.id)}
                      className={`py-1.5 px-2 rounded-lg text-center font-medium border transition-colors cursor-pointer ${
                        filters.recommendation === rec.id
                          ? 'bg-accent-green text-surface border-accent-green font-semibold shadow-xs'
                          : 'bg-surface-secondary border-border-primary text-tx-secondary hover:text-tx-primary'
                      }`}
                    >
                      {rec.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Price Change Performance */}
              <div className="space-y-1.5">
                <label htmlFor="screener-change-range" className="block text-xs font-medium text-tx-secondary">
                  Price Performance Range
                </label>
                <select
                  id="screener-change-range"
                  value={filters.changeRange}
                  onChange={(e) => updateField('changeRange', e.target.value)}
                  className="w-full px-3 py-2 bg-surface-secondary border border-border-primary rounded-xl text-xs sm:text-sm text-tx-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
                >
                  <option value="ALL">All Changes</option>
                  <option value="POSITIVE">Positive Gainers (&gt; 0%)</option>
                  <option value="NEGATIVE">Negative Decliners (&lt; 0%)</option>
                  <option value="STRONG_GAIN">Strong Gainers (&ge; +2.0%)</option>
                  <option value="STRONG_DECLINE">Strong Decliners (&le; -2.0%)</option>
                  <option value="FLAT">Flat (-0.5% to +0.5%)</option>
                </select>
              </div>

              {/* Market Price Range */}
              <div className="space-y-2">
                <label htmlFor="screener-price-range" className="block text-xs font-medium text-tx-secondary">
                  Market Price Range (₹)
                </label>
                <select
                  id="screener-price-range"
                  value={filters.priceRange}
                  onChange={(e) => updateField('priceRange', e.target.value)}
                  className="w-full px-3 py-2 bg-surface-secondary border border-border-primary rounded-xl text-xs sm:text-sm text-tx-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
                >
                  <option value="ALL">All Prices</option>
                  <option value="UNDER_500">Under ₹500</option>
                  <option value="500_TO_2000">₹500 to ₹2,000</option>
                  <option value="2000_TO_5000">₹2,000 to ₹5,000</option>
                  <option value="ABOVE_5000">Above ₹5,000</option>
                  <option value="CUSTOM">Custom Range...</option>
                </select>

                {/* Custom Min / Max Inputs */}
                {filters.priceRange === 'CUSTOM' && (
                  <div className="grid grid-cols-2 gap-2 pt-1 animate-in fade-in duration-150">
                    <div>
                      <label htmlFor="screener-min-price" className="sr-only">Min Price</label>
                      <input
                        id="screener-min-price"
                        type="number"
                        placeholder="Min ₹"
                        value={filters.minPrice}
                        onChange={(e) => updateField('minPrice', e.target.value)}
                        className="w-full px-3 py-1.5 bg-surface border border-border-primary rounded-lg text-xs font-mono text-tx-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
                      />
                    </div>
                    <div>
                      <label htmlFor="screener-max-price" className="sr-only">Max Price</label>
                      <input
                        id="screener-max-price"
                        type="number"
                        placeholder="Max ₹"
                        value={filters.maxPrice}
                        onChange={(e) => updateField('maxPrice', e.target.value)}
                        className="w-full px-3 py-1.5 bg-surface border border-border-primary rounded-lg text-xs font-mono text-tx-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* 3. DRAWER FOOTER */}
          <div className="p-4 border-t border-border-primary bg-surface-secondary/60 flex items-center justify-between gap-3 shrink-0">
            <div className="text-xs text-tx-secondary">
              Showing <strong className="text-tx-primary font-mono">{matchCount}</strong> of <span className="font-mono">{totalCount}</span> stocks
            </div>
            <div className="flex items-center gap-2">
              {activeCount > 0 && (
                <button
                  type="button"
                  onClick={onResetFilters}
                  className="px-3 py-2 rounded-xl border border-border-primary text-xs font-medium text-tx-secondary hover:text-tx-primary hover:bg-surface transition-colors cursor-pointer"
                >
                  Clear All
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-accent-green hover:bg-accent-green/90 text-surface text-xs font-semibold transition-all shadow-sm cursor-pointer"
              >
                View {matchCount} Results
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default ScreenerFilterDrawer;
