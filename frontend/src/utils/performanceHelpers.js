/**
 * @file performanceHelpers.js
 * @description Pure utility functions for portfolio performance calculations,
 * equity curve validation, SVG scaling math, and backtest data normalization.
 *
 * SPECIFICATION:
 *   - Strictly non-fabricated: Validates historical equity series before plotting.
 *   - Clear separation between simulated backtests and forward watchlist tracking.
 *   - Handles missing, null, and insufficient data gracefully.
 *   - Pure functions with no React or DOM dependencies.
 */

import { calculatePerformanceSinceAdded } from './watchlistStorage.js';

/**
 * Validates a historical equity curve series.
 *
 * @param {Array<object>} series
 * @returns {{
 *   isValid: boolean,
 *   validCount: number,
 *   cleanSeries: Array<object>,
 *   startEquity: number|null,
 *   endEquity: number|null,
 *   minEquity: number|null,
 *   maxEquity: number|null,
 *   totalReturnPct: number|null,
 *   maxDrawdownPct: number|null
 * }}
 */
export function validateEquitySeries(series) {
  if (!Array.isArray(series) || series.length < 2) {
    return {
      isValid: false,
      validCount: 0,
      cleanSeries: [],
      startEquity: null,
      endEquity: null,
      minEquity: null,
      maxEquity: null,
      totalReturnPct: null,
      maxDrawdownPct: null,
    };
  }

  const cleanSeries = [];
  let minEquity = Infinity;
  let maxEquity = -Infinity;
  let maxDrawdownPct = 0;

  for (const point of series) {
    if (!point || typeof point !== 'object') continue;

    const eq = point.equity != null && !isNaN(Number(point.equity)) ? Number(point.equity) : null;
    const date = point.date || point.timestamp || null;

    if (eq != null && eq > 0 && date) {
      const dd = point.drawdown_pct != null && !isNaN(Number(point.drawdown_pct))
        ? Math.abs(Number(point.drawdown_pct))
        : 0;

      cleanSeries.push({
        date: String(date),
        equity: eq,
        drawdown_pct: dd,
      });

      if (eq < minEquity) minEquity = eq;
      if (eq > maxEquity) maxEquity = eq;
      if (dd > maxDrawdownPct) maxDrawdownPct = dd;
    }
  }

  if (cleanSeries.length < 2) {
    return {
      isValid: false,
      validCount: cleanSeries.length,
      cleanSeries: [],
      startEquity: null,
      endEquity: null,
      minEquity: null,
      maxEquity: null,
      totalReturnPct: null,
      maxDrawdownPct: null,
    };
  }

  const startEquity = cleanSeries[0].equity;
  const endEquity = cleanSeries[cleanSeries.length - 1].equity;
  const totalReturnPct = startEquity > 0 ? ((endEquity - startEquity) / startEquity) * 100 : null;

  return {
    isValid: true,
    validCount: cleanSeries.length,
    cleanSeries,
    startEquity,
    endEquity,
    minEquity,
    maxEquity,
    totalReturnPct,
    maxDrawdownPct,
  };
}

/**
 * Filters an equity curve series by time range if length supports it.
 *
 * @param {Array<object>} series
 * @param {string} rangeKey - 'ALL' | '1Y' | '6M' | '3M'
 * @returns {Array<object>}
 */
export function filterEquitySeriesByRange(series, rangeKey = 'ALL') {
  if (!Array.isArray(series) || series.length === 0) return [];
  if (rangeKey === 'ALL') return series;

  const countMap = {
    '3M': 4,
    '6M': 7,
    '1Y': 13,
  };

  const neededPoints = countMap[rangeKey] || series.length;
  if (series.length <= neededPoints) return series;

  return series.slice(-neededPoints);
}

/**
 * Calculates SVG coordinates and nice ticks for an equity curve chart.
 *
 * @param {object} params
 * @param {Array<object>} params.series - Validated equity points
 * @param {number} params.width - SVG container width
 * @param {number} params.height - SVG container height
 * @param {object} [params.margin] - { top, right, bottom, left }
 * @returns {object|null} Scale mapping and SVG path definitions
 */
export function calculateEquityScales({
  series,
  width,
  height,
  margin = { top: 20, right: 65, bottom: 30, left: 20 },
}) {
  const validation = validateEquitySeries(series);
  if (!validation.isValid) return null;

  const data = validation.cleanSeries;
  const chartWidth = Math.max(width - margin.left - margin.right, 50);
  const chartHeight = Math.max(height - margin.top - margin.bottom, 50);

  // Buffer top and bottom by 5%
  const span = validation.maxEquity - validation.minEquity || 1000;
  const minPrice = Math.max(validation.minEquity - span * 0.05, 0);
  const maxPrice = validation.maxEquity + span * 0.05;
  const priceRange = maxPrice - minPrice || 1;

  const stepX = data.length > 1 ? chartWidth / (data.length - 1) : chartWidth;

  const getX = (idx) => margin.left + idx * stepX;
  const getY = (val) => margin.top + (1 - (val - minPrice) / priceRange) * chartHeight;

  // Generate SVG path strings
  const points = data.map((d, i) => `${getX(i).toFixed(1)},${getY(d.equity).toFixed(1)}`);
  const linePath = `M ${points.join(' L ')}`;

  const zeroY = margin.top + chartHeight;
  const areaPath = `M ${getX(0).toFixed(1)},${zeroY} L ${points.join(' L ')} L ${getX(data.length - 1).toFixed(1)},${zeroY} Z`;

  // Compute 4-5 nice round ticks
  const tickCount = 4;
  const tickStep = (maxPrice - minPrice) / tickCount;
  const yTicks = [];
  for (let i = 0; i <= tickCount; i++) {
    const val = minPrice + i * tickStep;
    yTicks.push({
      value: val,
      y: getY(val),
    });
  }

  return {
    chartWidth,
    chartHeight,
    margin,
    minPrice,
    maxPrice,
    linePath,
    areaPath,
    yTicks,
    getX,
    getY,
    pointsCount: data.length,
  };
}

/**
 * Computes watchlist portfolio performance metrics using Phase 17 reference prices.
 *
 * @param {Array<object>} watchlistItems - Items saved in WatchlistContext
 * @param {Array<object>} universeStocks - Live stock universe from getStocks()
 * @returns {object} Aggregated metrics
 */
export function calculateWatchlistPortfolioMetrics(watchlistItems = [], universeStocks = []) {
  if (!Array.isArray(watchlistItems) || watchlistItems.length === 0) {
    return {
      totalTracked: 0,
      pricedCount: 0,
      gainersCount: 0,
      declinersCount: 0,
      flatCount: 0,
      avgReturnSinceAdded: null,
      bestPerformer: null,
      worstPerformer: null,
      stocks: [],
    };
  }

  const lookup = new Map();
  if (Array.isArray(universeStocks)) {
    for (const s of universeStocks) {
      if (s.symbol) lookup.set(s.symbol.toUpperCase(), s);
    }
  }

  let totalReturnSum = 0;
  let pricedCount = 0;
  let gainersCount = 0;
  let declinersCount = 0;
  let flatCount = 0;

  let bestPerformer = null;
  let worstPerformer = null;

  const mergedStocks = watchlistItems.map((item) => {
    const sym = (item.symbol || '').toUpperCase();
    const live = lookup.get(sym);

    const currentPrice = live?.current_price ?? live?.price ?? null;
    const addedPrice = item.addedPrice != null && Number(item.addedPrice) > 0 ? Number(item.addedPrice) : null;
    const returnSinceAdded = calculatePerformanceSinceAdded(currentPrice, addedPrice);

    let priceDifference = null;
    if (currentPrice != null && addedPrice != null) {
      priceDifference = Number(currentPrice) - Number(addedPrice);
    }

    const mergedItem = {
      ...item,
      symbol: sym,
      company_name: live?.company_name || item.company_name || sym,
      sector: live?.sector || item.sector || '—',
      current_price: currentPrice,
      addedPrice,
      addedAt: item.addedAt || null,
      daily_change_percent: live?.change_percent ?? live?.price_change_percent ?? null,
      returnSinceAdded,
      priceDifference,
      opportunity_score: live?.opportunity_score ?? null,
      recommendation: live?.recommendation ?? null,
      isUnavailable: !live && currentPrice == null,
    };

    if (returnSinceAdded != null) {
      totalReturnSum += returnSinceAdded;
      pricedCount++;

      if (returnSinceAdded > 0) gainersCount++;
      else if (returnSinceAdded < 0) declinersCount++;
      else flatCount++;

      if (!bestPerformer || returnSinceAdded > bestPerformer.returnSinceAdded) {
        bestPerformer = mergedItem;
      }
      if (!worstPerformer || returnSinceAdded < worstPerformer.returnSinceAdded) {
        worstPerformer = mergedItem;
      }
    }

    return mergedItem;
  });

  const avgReturnSinceAdded = pricedCount > 0 ? totalReturnSum / pricedCount : null;

  return {
    totalTracked: watchlistItems.length,
    pricedCount,
    gainersCount,
    declinersCount,
    flatCount,
    avgReturnSinceAdded,
    bestPerformer,
    worstPerformer,
    stocks: mergedStocks,
  };
}

/**
 * Normalizes backtest payload safely, identifying present vs missing series.
 *
 * @param {object} payload - Backtest API response
 * @returns {object} Normalized backtest object
 */
export function normalizeBacktestData(payload) {
  if (!payload || typeof payload !== 'object') {
    return {
      strategy_name: 'Trend Momentum',
      period: 'Unavailable',
      run_id: null,
      start_date: null,
      end_date: null,
      symbols: [],
      total_trades: 0,
      closed_trades: 0,
      open_trades: 0,
      winning_trades: 0,
      losing_trades: 0,
      win_rate: null,
      profit_factor: null,
      total_return_pct: null,
      avg_trade_return_pct: null,
      avg_winning_trade_pct: null,
      avg_losing_trade_pct: null,
      max_drawdown_pct: null,
      sharpe_ratio: null,
      cagr: null,
      hasEquityCurve: false,
      equity_curve: [],
      hasMonthlyReturns: false,
      monthly_returns: [],
      last_updated: null,
    };
  }

  const equityValidation = validateEquitySeries(payload.equity_curve || payload.equitySeries);
  const hasMonthlyReturns = Array.isArray(payload.monthly_returns) && payload.monthly_returns.length > 0;

  const totalTrades = Number(payload.total_trades) || 0;
  const closedTrades = Number(payload.closed_trades) || totalTrades;
  const openTrades = Number(payload.open_trades) || 0;
  const winningTrades = Number(payload.winning_trades) || 0;
  const losingTrades = Number(payload.losing_trades) || 0;

  const winRate = payload.win_rate != null && !isNaN(Number(payload.win_rate))
    ? Number(payload.win_rate)
    : (closedTrades > 0 && winningTrades > 0 ? (winningTrades / closedTrades) * 100 : null);

  const profitFactor = payload.profit_factor != null && !isNaN(Number(payload.profit_factor))
    ? Number(payload.profit_factor)
    : null;

  const totalReturnPct = payload.total_return_pct != null && !isNaN(Number(payload.total_return_pct))
    ? Number(payload.total_return_pct)
    : (payload.cagr != null && !isNaN(Number(payload.cagr)) ? Number(payload.cagr) : null);

  const maxDrawdownPct = payload.max_drawdown_pct != null && !isNaN(Number(payload.max_drawdown_pct))
    ? Math.abs(Number(payload.max_drawdown_pct))
    : (payload.max_drawdown != null && !isNaN(Number(payload.max_drawdown))
      ? Math.abs(Number(payload.max_drawdown))
      : null);

  return {
    strategy_name: payload.strategy_name || 'Quantitative Swing Strategy',
    period: payload.period || (payload.start_date && payload.end_date ? `${payload.start_date} → ${payload.end_date}` : '1 Year'),
    run_id: payload.run_id || null,
    start_date: payload.start_date || null,
    end_date: payload.end_date || null,
    symbols: Array.isArray(payload.symbols) ? payload.symbols : [],
    total_trades: totalTrades,
    closed_trades: closedTrades,
    open_trades: openTrades,
    winning_trades: winningTrades,
    losing_trades: losingTrades,
    win_rate: winRate,
    profit_factor: profitFactor,
    total_return_pct: totalReturnPct,
    avg_trade_return_pct: payload.avg_trade_return_pct != null ? Number(payload.avg_trade_return_pct) : null,
    avg_winning_trade_pct: payload.avg_winning_trade_pct != null ? Number(payload.avg_winning_trade_pct) : null,
    avg_losing_trade_pct: payload.avg_losing_trade_pct != null ? Number(payload.avg_losing_trade_pct) : null,
    max_drawdown_pct: maxDrawdownPct,
    sharpe_ratio: payload.sharpe_ratio != null && !isNaN(Number(payload.sharpe_ratio)) ? Number(payload.sharpe_ratio) : null,
    cagr: payload.cagr != null && !isNaN(Number(payload.cagr)) ? Number(payload.cagr) : null,
    hasEquityCurve: equityValidation.isValid,
    equity_curve: equityValidation.cleanSeries,
    hasMonthlyReturns,
    monthly_returns: hasMonthlyReturns ? payload.monthly_returns : [],
    last_updated: payload.last_updated || null,
  };
}
