/**
 * @file screenerFilters.js
 * @description Pure utility functions for technical stock screening, filtering, sorting, and active filter chip derivation.
 * 
 * DESIGN PRINCIPLES:
 *   - Pure functions with no React or DOM dependencies.
 *   - Strictly non-fabricated: technical filters require valid calculated indicator values.
 *   - Reuses Phase 15 technical indicator utilities.
 *   - Handles missing, null, and insufficient data safely.
 */

import { computeAllIndicators } from './technicalIndicators.js';

/**
 * Default empty screener filter state.
 */
export const DEFAULT_SCREENER_FILTERS = {
  search: '',
  sector: 'ALL',
  direction: 'ALL', // 'ALL' | 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  recommendation: 'ALL', // 'ALL' | 'BUY' | 'WATCH' | 'SELL'
  changeRange: 'ALL', // 'ALL' | 'POSITIVE' | 'NEGATIVE' | 'STRONG_GAIN' | 'STRONG_DECLINE' | 'FLAT'
  priceRange: 'ALL', // 'ALL' | 'UNDER_500' | '500_TO_2000' | '2000_TO_5000' | 'ABOVE_5000' | 'CUSTOM'
  minPrice: '',
  maxPrice: '',
  // Technical Strategy Filters:
  priceVsEma20: 'ALL', // 'ALL' | 'ABOVE' | 'BELOW'
  priceVsEma50: 'ALL', // 'ALL' | 'ABOVE' | 'BELOW'
  priceVsEma200: 'ALL', // 'ALL' | 'ABOVE' | 'BELOW'
  rsiRange: 'ALL', // 'ALL' | 'OVERSOLD' (<30) | 'NEUTRAL_LOW' (30-50) | 'NEUTRAL_HIGH' (50-70) | 'OVERBOUGHT' (>70)
  macdVsSignal: 'ALL', // 'ALL' | 'ABOVE' | 'BELOW'
  macdHistogram: 'ALL', // 'ALL' | 'POSITIVE' | 'NEGATIVE'
};

/**
 * Extracts a concise technical indicator snapshot from historical daily bars.
 * 
 * @param {Array<object>} historyData - Array of daily OHLCV candles
 * @returns {object} Technical indicator snapshot
 */
export function getTechnicalSnapshot(historyData) {
  if (!Array.isArray(historyData) || historyData.length === 0) {
    return {
      ema20: null,
      ema50: null,
      ema200: null,
      rsi: null,
      macd: null,
      signal: null,
      histogram: null,
      close: null,
      sufficiency: {
        totalBars: 0,
        hasEma20: false,
        hasEma50: false,
        hasEma200: false,
        hasRsi: false,
        hasMacd: false,
      },
      isInsufficient: true,
      historyLength: 0,
    };
  }

  const computed = computeAllIndicators(historyData);
  const latest = computed.latest || {};
  const sufficiency = computed.sufficiency || {};

  return {
    ema20: latest.ema20 ?? null,
    ema50: latest.ema50 ?? null,
    ema200: latest.ema200 ?? null,
    rsi: latest.rsi ?? null,
    macd: latest.macd ?? null,
    signal: latest.signal ?? null,
    histogram: latest.histogram ?? null,
    close: latest.close ?? null,
    sufficiency,
    isInsufficient: sufficiency.totalBars < 15,
    historyLength: sufficiency.totalBars || 0,
  };
}

/**
 * Checks if a single stock matches the given screener filter criteria.
 * 
 * @param {object} stock - Stock object
 * @param {object} filters - Active screener filters
 * @param {object} [technicals] - Technical snapshot for the stock
 * @returns {boolean} True if stock satisfies all active filters
 */
export function matchesScreenerFilters(stock, filters, technicals = null) {
  if (!stock) return false;

  // 1. Search Query (Symbol, Company Name, Sector, Industry)
  if (filters.search && filters.search.trim()) {
    const q = filters.search.toLowerCase().trim();
    const symMatch = (stock.symbol || '').toLowerCase().includes(q);
    const nameMatch = (stock.company_name || '').toLowerCase().includes(q);
    const secMatch = (stock.sector || '').toLowerCase().includes(q);
    const indMatch = (stock.industry || '').toLowerCase().includes(q);
    if (!symMatch && !nameMatch && !secMatch && !indMatch) {
      return false;
    }
  }

  // 2. Sector Filter
  if (filters.sector && filters.sector !== 'ALL') {
    if (stock.sector !== filters.sector) {
      return false;
    }
  }

  // 3. Direction Filter (Bullish / Bearish / Neutral)
  if (filters.direction && filters.direction !== 'ALL') {
    const dir = (stock.direction || stock.recommendation || '').toUpperCase();
    if (filters.direction === 'BULLISH' && dir !== 'BUY' && dir !== 'BULLISH') return false;
    if (filters.direction === 'BEARISH' && dir !== 'SELL' && dir !== 'BEARISH') return false;
    if (filters.direction === 'NEUTRAL' && dir !== 'WATCH' && dir !== 'NEUTRAL' && dir !== 'HOLD') return false;
  }

  // 4. Recommendation Filter
  if (filters.recommendation && filters.recommendation !== 'ALL') {
    const rec = (stock.recommendation || '').toUpperCase();
    if (filters.recommendation === 'BUY' && rec !== 'BUY' && rec !== 'BULLISH') return false;
    if (filters.recommendation === 'WATCH' && rec !== 'WATCH') return false;
    if (filters.recommendation === 'SELL' && rec !== 'SELL' && rec !== 'BEARISH') return false;
  }

  // 5. Price Change / Performance Range Filter
  const priceChange = stock.change_percent ?? stock.price_change_percent;
  if (filters.changeRange && filters.changeRange !== 'ALL') {
    if (priceChange == null || isNaN(priceChange)) return false;
    const chg = Number(priceChange);

    switch (filters.changeRange) {
      case 'POSITIVE':
        if (chg < 0) return false;
        break;
      case 'NEGATIVE':
        if (chg >= 0) return false;
        break;
      case 'STRONG_GAIN':
        if (chg < 2.0) return false;
        break;
      case 'STRONG_DECLINE':
        if (chg > -2.0) return false;
        break;
      case 'FLAT':
        if (chg < -0.5 || chg > 0.5) return false;
        break;
      default:
        break;
    }
  }

  // 6. Market Price Range Filter
  const stockPrice = stock.current_price ?? stock.price ?? technicals?.close;
  if (stockPrice != null && !isNaN(stockPrice)) {
    const p = Number(stockPrice);

    if (filters.minPrice !== '' && !isNaN(Number(filters.minPrice))) {
      if (p < Number(filters.minPrice)) return false;
    }
    if (filters.maxPrice !== '' && !isNaN(Number(filters.maxPrice))) {
      if (p > Number(filters.maxPrice)) return false;
    }

    if (filters.priceRange && filters.priceRange !== 'ALL' && filters.priceRange !== 'CUSTOM') {
      switch (filters.priceRange) {
        case 'UNDER_500':
          if (p >= 500) return false;
          break;
        case '500_TO_2000':
          if (p < 500 || p > 2000) return false;
          break;
        case '2000_TO_5000':
          if (p < 2000 || p > 5000) return false;
          break;
        case 'ABOVE_5000':
          if (p <= 5000) return false;
          break;
        default:
          break;
      }
    }
  } else if (
    filters.minPrice !== '' ||
    filters.maxPrice !== '' ||
    (filters.priceRange && filters.priceRange !== 'ALL')
  ) {
    // If a price filter is applied but stock has no valid price, exclude it
    return false;
  }

  // 7. Technical Strategy Filters
  // CRITICAL RULE: If a technical indicator filter is active, require valid calculated values.
  // Never fabricate missing indicators for stocks with insufficient data.
  const evalPrice = stockPrice != null ? Number(stockPrice) : null;

  // Price vs EMA 20
  if (filters.priceVsEma20 && filters.priceVsEma20 !== 'ALL') {
    if (!technicals || technicals.ema20 == null || evalPrice == null) return false;
    if (filters.priceVsEma20 === 'ABOVE' && evalPrice <= technicals.ema20) return false;
    if (filters.priceVsEma20 === 'BELOW' && evalPrice >= technicals.ema20) return false;
  }

  // Price vs EMA 50
  if (filters.priceVsEma50 && filters.priceVsEma50 !== 'ALL') {
    if (!technicals || technicals.ema50 == null || evalPrice == null) return false;
    if (filters.priceVsEma50 === 'ABOVE' && evalPrice <= technicals.ema50) return false;
    if (filters.priceVsEma50 === 'BELOW' && evalPrice >= technicals.ema50) return false;
  }

  // Price vs EMA 200
  if (filters.priceVsEma200 && filters.priceVsEma200 !== 'ALL') {
    if (!technicals || technicals.ema200 == null || evalPrice == null) return false;
    if (filters.priceVsEma200 === 'ABOVE' && evalPrice <= technicals.ema200) return false;
    if (filters.priceVsEma200 === 'BELOW' && evalPrice >= technicals.ema200) return false;
  }

  // RSI Range (14)
  if (filters.rsiRange && filters.rsiRange !== 'ALL') {
    if (!technicals || technicals.rsi == null) return false;
    const rsi = technicals.rsi;
    switch (filters.rsiRange) {
      case 'OVERSOLD':
        if (rsi >= 30) return false;
        break;
      case 'NEUTRAL_LOW':
        if (rsi < 30 || rsi > 50) return false;
        break;
      case 'NEUTRAL_HIGH':
        if (rsi <= 50 || rsi > 70) return false;
        break;
      case 'OVERBOUGHT':
        if (rsi <= 70) return false;
        break;
      default:
        break;
    }
  }

  // MACD vs Signal
  if (filters.macdVsSignal && filters.macdVsSignal !== 'ALL') {
    if (!technicals || technicals.macd == null || technicals.signal == null) return false;
    if (filters.macdVsSignal === 'ABOVE' && technicals.macd <= technicals.signal) return false;
    if (filters.macdVsSignal === 'BELOW' && technicals.macd >= technicals.signal) return false;
  }

  // MACD Histogram
  if (filters.macdHistogram && filters.macdHistogram !== 'ALL') {
    if (!technicals || technicals.histogram == null) return false;
    if (filters.macdHistogram === 'POSITIVE' && technicals.histogram <= 0) return false;
    if (filters.macdHistogram === 'NEGATIVE' && technicals.histogram >= 0) return false;
  }

  return true;
}

/**
 * Filters a list of stocks using active filters and an optional map of technical snapshots.
 * 
 * @param {Array<object>} stocks - List of stocks
 * @param {object} filters - Active screener filters
 * @param {Map<string, object>|object} [technicalsMap] - Map of symbol -> technical snapshot
 * @returns {Array<object>} Filtered stocks
 */
export function filterStocks(stocks, filters, technicalsMap = null) {
  if (!Array.isArray(stocks)) return [];

  return stocks.filter((stock) => {
    const sym = (stock.symbol || '').toUpperCase().trim();
    let tech = null;
    if (technicalsMap) {
      tech = technicalsMap instanceof Map ? technicalsMap.get(sym) : technicalsMap[sym];
    }
    return matchesScreenerFilters(stock, filters, tech);
  });
}

/**
 * Sorts an array of stocks by the selected sort key.
 * 
 * @param {Array<object>} stocks - List of stocks
 * @param {string} sortBy - Sort key
 * @param {Map<string, object>|object} [technicalsMap]
 * @returns {Array<object>} Sorted stocks (shallow copy)
 */
export function sortStocks(stocks, sortBy = 'symbol-asc', technicalsMap = null) {
  if (!Array.isArray(stocks)) return [];

  const copy = [...stocks];

  const getTech = (stock) => {
    if (!technicalsMap) return null;
    const sym = (stock.symbol || '').toUpperCase().trim();
    return technicalsMap instanceof Map ? technicalsMap.get(sym) : technicalsMap[sym];
  };

  return copy.sort((a, b) => {
    const changeA = a.change_percent ?? a.price_change_percent ?? 0;
    const changeB = b.change_percent ?? b.price_change_percent ?? 0;
    const priceA = a.current_price ?? a.price ?? 0;
    const priceB = b.current_price ?? b.price ?? 0;

    switch (sortBy) {
      case 'symbol-asc':
        return (a.symbol || '').localeCompare(b.symbol || '');
      case 'symbol-desc':
        return (b.symbol || '').localeCompare(a.symbol || '');
      case 'price-desc':
        return priceB - priceA;
      case 'price-asc':
        return priceA - priceB;
      case 'change-desc':
        return changeB - changeA;
      case 'change-asc':
        return changeA - changeB;
      case 'score-desc':
        return (b.opportunity_score ?? 0) - (a.opportunity_score ?? 0);
      case 'score-asc':
        return (a.opportunity_score ?? 0) - (b.opportunity_score ?? 0);
      case 'rsi-desc': {
        const rsiA = getTech(a)?.rsi ?? -Infinity;
        const rsiB = getTech(b)?.rsi ?? -Infinity;
        return rsiB - rsiA;
      }
      case 'rsi-asc': {
        const rsiA = getTech(a)?.rsi ?? Infinity;
        const rsiB = getTech(b)?.rsi ?? Infinity;
        return rsiA - rsiB;
      }
      case 'recommendation-asc':
        return (a.recommendation || '').localeCompare(b.recommendation || '');
      case 'recommendation-desc':
        return (b.recommendation || '').localeCompare(a.recommendation || '');
      default:
        return 0;
    }
  });
}

/**
 * Counts the number of active, non-default screener filters.
 * 
 * @param {object} filters
 * @returns {number} Active filter count
 */
export function countActiveFilters(filters) {
  if (!filters) return 0;
  let count = 0;

  if (filters.search && filters.search.trim()) count++;
  if (filters.sector && filters.sector !== 'ALL') count++;
  if (filters.direction && filters.direction !== 'ALL') count++;
  if (filters.recommendation && filters.recommendation !== 'ALL') count++;
  if (filters.changeRange && filters.changeRange !== 'ALL') count++;
  if (filters.priceRange && filters.priceRange !== 'ALL') count++;
  if (filters.minPrice !== '' || filters.maxPrice !== '') count++;
  if (filters.priceVsEma20 && filters.priceVsEma20 !== 'ALL') count++;
  if (filters.priceVsEma50 && filters.priceVsEma50 !== 'ALL') count++;
  if (filters.priceVsEma200 && filters.priceVsEma200 !== 'ALL') count++;
  if (filters.rsiRange && filters.rsiRange !== 'ALL') count++;
  if (filters.macdVsSignal && filters.macdVsSignal !== 'ALL') count++;
  if (filters.macdHistogram && filters.macdHistogram !== 'ALL') count++;

  return count;
}

/**
 * Generates human-readable active filter chip objects with removal callbacks.
 * 
 * @param {object} filters - Current active filters
 * @param {Function} onRemove - Callback invoked with the filter key to reset
 * @returns {Array<{id: string, key: string, label: string, onRemove: Function}>}
 */
export function getActiveFilterChips(filters, onRemove) {
  if (!filters) return [];
  const chips = [];

  if (filters.search && filters.search.trim()) {
    chips.push({
      id: 'search',
      key: 'search',
      label: `Search: "${filters.search.trim()}"`,
      onRemove: () => onRemove('search', ''),
    });
  }

  if (filters.sector && filters.sector !== 'ALL') {
    chips.push({
      id: 'sector',
      key: 'sector',
      label: `Sector: ${filters.sector}`,
      onRemove: () => onRemove('sector', 'ALL'),
    });
  }

  if (filters.direction && filters.direction !== 'ALL') {
    chips.push({
      id: 'direction',
      key: 'direction',
      label: `Direction: ${filters.direction}`,
      onRemove: () => onRemove('direction', 'ALL'),
    });
  }

  if (filters.recommendation && filters.recommendation !== 'ALL') {
    chips.push({
      id: 'recommendation',
      key: 'recommendation',
      label: `Signal: ${filters.recommendation}`,
      onRemove: () => onRemove('recommendation', 'ALL'),
    });
  }

  if (filters.changeRange && filters.changeRange !== 'ALL') {
    const labels = {
      POSITIVE: 'Change: Gainers (+)',
      NEGATIVE: 'Change: Decliners (-)',
      STRONG_GAIN: 'Change: > +2%',
      STRONG_DECLINE: 'Change: < -2%',
      FLAT: 'Change: Flat (-0.5% to +0.5%)',
    };
    chips.push({
      id: 'changeRange',
      key: 'changeRange',
      label: labels[filters.changeRange] || `Change: ${filters.changeRange}`,
      onRemove: () => onRemove('changeRange', 'ALL'),
    });
  }

  if (filters.priceRange && filters.priceRange !== 'ALL') {
    const labels = {
      UNDER_500: 'Price: < ₹500',
      '500_TO_2000': 'Price: ₹500–₹2,000',
      '2000_TO_5000': 'Price: ₹2,000–₹5,000',
      ABOVE_5000: 'Price: > ₹5,000',
      CUSTOM: `Price: ₹${filters.minPrice || 0} - ₹${filters.maxPrice || '∞'}`,
    };
    chips.push({
      id: 'priceRange',
      key: 'priceRange',
      label: labels[filters.priceRange] || `Price: ${filters.priceRange}`,
      onRemove: () => {
        onRemove('priceRange', 'ALL');
        onRemove('minPrice', '');
        onRemove('maxPrice', '');
      },
    });
  } else if (filters.minPrice !== '' || filters.maxPrice !== '') {
    chips.push({
      id: 'customPrice',
      key: 'customPrice',
      label: `Price: ₹${filters.minPrice || 0} – ₹${filters.maxPrice || '∞'}`,
      onRemove: () => {
        onRemove('minPrice', '');
        onRemove('maxPrice', '');
      },
    });
  }

  // Technical Indicator Filter Chips
  if (filters.priceVsEma20 && filters.priceVsEma20 !== 'ALL') {
    chips.push({
      id: 'priceVsEma20',
      key: 'priceVsEma20',
      label: `Price ${filters.priceVsEma20 === 'ABOVE' ? '>' : '<'} EMA 20`,
      onRemove: () => onRemove('priceVsEma20', 'ALL'),
    });
  }

  if (filters.priceVsEma50 && filters.priceVsEma50 !== 'ALL') {
    chips.push({
      id: 'priceVsEma50',
      key: 'priceVsEma50',
      label: `Price ${filters.priceVsEma50 === 'ABOVE' ? '>' : '<'} EMA 50`,
      onRemove: () => onRemove('priceVsEma50', 'ALL'),
    });
  }

  if (filters.priceVsEma200 && filters.priceVsEma200 !== 'ALL') {
    chips.push({
      id: 'priceVsEma200',
      key: 'priceVsEma200',
      label: `Price ${filters.priceVsEma200 === 'ABOVE' ? '>' : '<'} EMA 200`,
      onRemove: () => onRemove('priceVsEma200', 'ALL'),
    });
  }

  if (filters.rsiRange && filters.rsiRange !== 'ALL') {
    const labels = {
      OVERSOLD: 'RSI < 30 (Oversold)',
      NEUTRAL_LOW: 'RSI 30–50',
      NEUTRAL_HIGH: 'RSI 50–70',
      OVERBOUGHT: 'RSI > 70 (Overbought)',
    };
    chips.push({
      id: 'rsiRange',
      key: 'rsiRange',
      label: labels[filters.rsiRange] || `RSI: ${filters.rsiRange}`,
      onRemove: () => onRemove('rsiRange', 'ALL'),
    });
  }

  if (filters.macdVsSignal && filters.macdVsSignal !== 'ALL') {
    chips.push({
      id: 'macdVsSignal',
      key: 'macdVsSignal',
      label: `MACD ${filters.macdVsSignal === 'ABOVE' ? '>' : '<'} Signal`,
      onRemove: () => onRemove('macdVsSignal', 'ALL'),
    });
  }

  if (filters.macdHistogram && filters.macdHistogram !== 'ALL') {
    chips.push({
      id: 'macdHistogram',
      key: 'macdHistogram',
      label: `MACD Hist: ${filters.macdHistogram === 'POSITIVE' ? 'Positive (>0)' : 'Negative (<0)'}`,
      onRemove: () => onRemove('macdHistogram', 'ALL'),
    });
  }

  return chips;
}

/**
 * Standard strategy presets for 1-click screener configuration.
 */
export const SCREENER_PRESETS = [
  {
    id: 'bullish_momentum',
    label: 'Bullish Momentum',
    description: 'Price > EMA 20, MACD > Signal, RSI 50–70',
    filters: {
      priceVsEma20: 'ABOVE',
      macdVsSignal: 'ABOVE',
      rsiRange: 'NEUTRAL_HIGH',
      direction: 'BULLISH',
    },
  },
  {
    id: 'oversold_pullback',
    label: 'Oversold Pullback',
    description: 'RSI < 30 & Price > EMA 200 long-term support',
    filters: {
      rsiRange: 'OVERSOLD',
      priceVsEma200: 'ABOVE',
    },
  },
  {
    id: 'trend_following',
    label: 'Trend Following',
    description: 'Price above both EMA 50 & EMA 200',
    filters: {
      priceVsEma50: 'ABOVE',
      priceVsEma200: 'ABOVE',
      changeRange: 'POSITIVE',
    },
  },
  {
    id: 'bearish_pressure',
    label: 'Bearish Breakdown',
    description: 'Price < EMA 50, MACD < Signal, Negative Histogram',
    filters: {
      priceVsEma50: 'BELOW',
      macdVsSignal: 'BELOW',
      macdHistogram: 'NEGATIVE',
      direction: 'BEARISH',
    },
  },
];
