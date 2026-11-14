/**
 * @file technicalIndicators.js
 * @description Pure utility functions for calculating financial technical indicators (EMA, RSI, MACD).
 * 
 * DESIGN PRINCIPLES:
 *   - Pure mathematical calculations with no DOM or React dependencies.
 *   - Strictly non-fabricated: returns null for periods with insufficient historical data.
 *   - Handles edge cases safely (constant prices, missing fields, zero loss, empty arrays).
 *   - Adheres to standard financial definitions (Wilder's RSI, standard EMA smoothing, MACD 12/26/9).
 */

/**
 * Extracts a numeric price from a data point.
 * 
 * @param {object|number} item
 * @param {string} [priceKey='close']
 * @returns {number|null}
 */
export function getPrice(item, priceKey = 'close') {
  if (item == null) return null;
  if (typeof item === 'number') {
    return isNaN(item) ? null : item;
  }
  const val = item[priceKey] != null ? item[priceKey] : item.close;
  const num = Number(val);
  return isNaN(num) ? null : num;
}

/**
 * Calculates Exponential Moving Average (EMA) for a specified period.
 * 
 * Formula:
 *   Multiplier k = 2 / (period + 1)
 *   Initial EMA = Simple Moving Average (SMA) of first `period` prices
 *   EMA_t = Price_t * k + EMA_{t-1} * (1 - k)
 * 
 * @param {Array<object|number>} data - Chronological array of candles or numbers
 * @param {number} period - Number of periods (e.g. 20, 50, 200)
 * @param {string} [priceKey='close'] - Key for price field
 * @returns {Array<number|null>} Array of same length as data, with null for indices < period - 1
 */
export function calculateEMA(data, period, priceKey = 'close') {
  if (!Array.isArray(data) || data.length === 0 || !period || period < 1) {
    return [];
  }

  const len = data.length;
  const result = new Array(len).fill(null);

  if (len < period) {
    return result;
  }

  const k = 2 / (period + 1);

  // Check if first `period` prices are valid numbers to compute the initial SMA
  let sum = 0;
  for (let i = 0; i < period; i++) {
    const p = getPrice(data[i], priceKey);
    if (p == null) {
      // Cannot calculate SMA if missing prices in the window
      return result;
    }
    sum += p;
  }

  let prevEMA = sum / period;
  result[period - 1] = Math.round(prevEMA * 100) / 100;

  for (let i = period; i < len; i++) {
    const price = getPrice(data[i], priceKey);
    if (price == null) {
      result[i] = null;
      continue;
    }
    const currentEMA = price * k + prevEMA * (1 - k);
    result[i] = Math.round(currentEMA * 100) / 100;
    prevEMA = currentEMA;
  }

  return result;
}

/**
 * Calculates Relative Strength Index (RSI) using standard 14-period Wilder's smoothing.
 * 
 * Formula:
 *   Gains / Losses over price changes Delta_i = P_i - P_{i-1}
 *   First AvgGain = sum(Gains, 14) / 14
 *   First AvgLoss = sum(Losses, 14) / 14
 *   Subsequent: AvgGain_t = (AvgGain_{t-1} * 13 + Gain_t) / 14
 *               AvgLoss_t = (AvgLoss_{t-1} * 13 + Loss_t) / 14
 *   RS = AvgGain / AvgLoss
 *   RSI = 100 - (100 / (1 + RS))
 * 
 * Special edge cases:
 *   - Constant prices (AvgGain == 0, AvgLoss == 0): RSI = 50 (neutral)
 *   - No losses (AvgLoss == 0, AvgGain > 0): RSI = 100
 *   - No gains (AvgGain == 0, AvgLoss > 0): RSI = 0
 * 
 * @param {Array<object|number>} data - Chronological array of candles or numbers
 * @param {number} [period=14] - Period for RSI (standard: 14)
 * @param {string} [priceKey='close'] - Key for price field
 * @returns {Array<number|null>} Array of same length as data, with null for indices < period
 */
export function calculateRSI(data, period = 14, priceKey = 'close') {
  if (!Array.isArray(data) || data.length === 0 || !period || period < 1) {
    return [];
  }

  const len = data.length;
  const result = new Array(len).fill(null);

  // RSI needs at least period + 1 prices to compute period price differences
  if (len <= period) {
    return result;
  }

  // Calculate changes
  let gainSum = 0;
  let lossSum = 0;

  for (let i = 1; i <= period; i++) {
    const curr = getPrice(data[i], priceKey);
    const prev = getPrice(data[i - 1], priceKey);

    if (curr == null || prev == null) {
      return result;
    }

    const change = curr - prev;
    if (change > 0) {
      gainSum += change;
    } else {
      lossSum += Math.abs(change);
    }
  }

  let avgGain = gainSum / period;
  let avgLoss = lossSum / period;

  const computeRsiFromAverages = (ag, al) => {
    if (al === 0) {
      return ag === 0 ? 50 : 100;
    }
    const rs = ag / al;
    const rsi = 100 - 100 / (1 + rs);
    return Math.min(Math.max(Math.round(rsi * 100) / 100, 0), 100);
  };

  result[period] = computeRsiFromAverages(avgGain, avgLoss);

  for (let i = period + 1; i < len; i++) {
    const curr = getPrice(data[i], priceKey);
    const prev = getPrice(data[i - 1], priceKey);

    if (curr == null || prev == null) {
      result[i] = null;
      continue;
    }

    const change = curr - prev;
    const gain = change > 0 ? change : 0;
    const loss = change < 0 ? Math.abs(change) : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;

    result[i] = computeRsiFromAverages(avgGain, avgLoss);
  }

  return result;
}

/**
 * Calculates Moving Average Convergence Divergence (MACD).
 * 
 * Standard settings:
 *   Fast EMA: 12 periods
 *   Slow EMA: 26 periods
 *   Signal Line: 9-period EMA of MACD Line
 *   Histogram: MACD Line - Signal Line
 * 
 * @param {Array<object|number>} data - Chronological array of candles or numbers
 * @param {object} [options]
 * @param {number} [options.fastPeriod=12]
 * @param {number} [options.slowPeriod=26]
 * @param {number} [options.signalPeriod=9]
 * @param {string} [priceKey='close']
 * @returns {Array<{macd: number|null, signal: number|null, histogram: number|null}>}
 */
export function calculateMACD(
  data,
  { fastPeriod = 12, slowPeriod = 26, signalPeriod = 9 } = {},
  priceKey = 'close'
) {
  if (!Array.isArray(data) || data.length === 0) {
    return [];
  }

  const len = data.length;
  const result = new Array(len).fill(null).map(() => ({
    macd: null,
    signal: null,
    histogram: null,
  }));

  if (len < slowPeriod) {
    return result;
  }

  const fastEMA = calculateEMA(data, fastPeriod, priceKey);
  const slowEMA = calculateEMA(data, slowPeriod, priceKey);

  // MACD line is valid from index slowPeriod - 1 onwards
  const macdValues = new Array(len).fill(null);
  for (let i = slowPeriod - 1; i < len; i++) {
    if (fastEMA[i] != null && slowEMA[i] != null) {
      macdValues[i] = fastEMA[i] - slowEMA[i];
      result[i].macd = Math.round(macdValues[i] * 100) / 100;
    }
  }

  // Calculate Signal line: 9-period EMA of the MACD line
  // The MACD line starts having valid values at index startIndex = slowPeriod - 1
  const startIndex = slowPeriod - 1;
  const minRequiredLength = startIndex + signalPeriod;

  if (len < minRequiredLength) {
    return result;
  }

  // Calculate initial SMA of the first `signalPeriod` MACD values
  let sumMacd = 0;
  for (let i = startIndex; i < minRequiredLength; i++) {
    if (macdValues[i] == null) {
      return result;
    }
    sumMacd += macdValues[i];
  }

  const signalK = 2 / (signalPeriod + 1);
  let prevSignal = sumMacd / signalPeriod;

  const firstSignalIndex = minRequiredLength - 1;
  result[firstSignalIndex].signal = Math.round(prevSignal * 100) / 100;
  if (result[firstSignalIndex].macd != null) {
    result[firstSignalIndex].histogram =
      Math.round((result[firstSignalIndex].macd - result[firstSignalIndex].signal) * 100) / 100;
  }

  for (let i = minRequiredLength; i < len; i++) {
    const currentMacd = macdValues[i];
    if (currentMacd == null) {
      result[i].signal = null;
      result[i].histogram = null;
      continue;
    }

    const currentSignal = currentMacd * signalK + prevSignal * (1 - signalK);
    result[i].signal = Math.round(currentSignal * 100) / 100;
    result[i].histogram = Math.round((currentMacd - currentSignal) * 100) / 100;
    prevSignal = currentSignal;
  }

  return result;
}

/**
 * Computes all technical indicators for a full historical dataset.
 * 
 * @param {Array<object>} fullHistory - Complete daily candle records
 * @returns {object} Complete indicator series and latest metrics
 */
export function computeAllIndicators(fullHistory = []) {
  if (!Array.isArray(fullHistory) || fullHistory.length === 0) {
    return {
      ema20: [],
      ema50: [],
      ema200: [],
      rsi14: [],
      macd: [],
      sufficiency: {
        totalBars: 0,
        hasEma20: false,
        hasEma50: false,
        hasEma200: false,
        hasRsi: false,
        hasMacd: false,
      },
      latest: null,
    };
  }

  const ema20 = calculateEMA(fullHistory, 20, 'close');
  const ema50 = calculateEMA(fullHistory, 50, 'close');
  const ema200 = calculateEMA(fullHistory, 200, 'close');
  const rsi14 = calculateRSI(fullHistory, 14, 'close');
  const macd = calculateMACD(fullHistory, { fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 }, 'close');

  const totalBars = fullHistory.length;
  const lastIndex = totalBars - 1;

  const latestCandle = fullHistory[lastIndex];
  const latestClose = latestCandle?.close != null ? Number(latestCandle.close) : null;

  const latestEma20 = ema20[lastIndex] ?? null;
  const latestEma50 = ema50[lastIndex] ?? null;
  const latestEma200 = ema200[lastIndex] ?? null;
  const latestRsi = rsi14[lastIndex] ?? null;
  const latestMacdObj = macd[lastIndex] ?? { macd: null, signal: null, histogram: null };

  const sufficiency = {
    totalBars,
    hasEma20: totalBars >= 20 && latestEma20 !== null,
    hasEma50: totalBars >= 50 && latestEma50 !== null,
    hasEma200: totalBars >= 200 && latestEma200 !== null,
    hasRsi: totalBars >= 15 && latestRsi !== null,
    hasMacd: totalBars >= 34 && latestMacdObj.signal !== null,
  };

  const latest = {
    date: latestCandle?.date,
    close: latestClose,
    ema20: latestEma20,
    ema50: latestEma50,
    ema200: latestEma200,
    rsi: latestRsi,
    macd: latestMacdObj.macd,
    signal: latestMacdObj.signal,
    histogram: latestMacdObj.histogram,
  };

  return {
    ema20,
    ema50,
    ema200,
    rsi14,
    macd,
    sufficiency,
    latest,
  };
}

/**
 * Classifies an RSI value into standard momentum zones.
 * 
 * Educational Disclaimer:
 *   RSI is a momentum oscillator. Overbought/oversold levels indicate extreme momentum
 *   and potential exhaustion, not guaranteed price reversals or automatic trading signals.
 * 
 * @param {number|null} rsiValue
 * @returns {object} Zone classification, styling badges, and descriptive explanation
 */
export function getRsiZone(rsiValue) {
  if (rsiValue == null || isNaN(rsiValue)) {
    return {
      zone: 'INSUFFICIENT',
      label: 'Insufficient Data',
      colorClass: 'text-tx-muted',
      badgeClass: 'bg-surface-secondary text-tx-secondary border-border-primary',
      description: 'Requires at least 15 trading days of historical closing prices.',
    };
  }

  const num = Number(rsiValue);

  if (num >= 70) {
    return {
      zone: 'OVERBOUGHT',
      label: 'Overbought (>70)',
      colorClass: 'text-accent-orange',
      badgeClass: 'bg-accent-orange/10 text-accent-orange border-accent-orange/30',
      description: 'Price momentum has reached upper statistical levels; indicates extended upward movement rather than a certain sell signal.',
    };
  }

  if (num <= 30) {
    return {
      zone: 'OVERSOLD',
      label: 'Oversold (<30)',
      colorClass: 'text-accent-teal',
      badgeClass: 'bg-accent-teal/10 text-accent-teal border-accent-teal/30',
      description: 'Price momentum has reached lower statistical levels; indicates extended downward pressure rather than a certain buy signal.',
    };
  }

  return {
    zone: 'NEUTRAL',
    label: 'Neutral Range (30–70)',
    colorClass: 'text-tx-secondary',
    badgeClass: 'bg-surface-secondary text-tx-secondary border-border-primary',
    description: 'Momentum is balanced within the customary baseline range (30 to 70).',
  };
}

/**
 * Classifies MACD state and momentum direction.
 * 
 * @param {number|null} macdVal
 * @param {number|null} signalVal
 * @param {number|null} histVal
 * @returns {object} MACD status details and styling
 */
export function getMacdStatus(macdVal, signalVal, histVal) {
  if (macdVal == null || signalVal == null || histVal == null) {
    return {
      status: 'INSUFFICIENT',
      label: 'Insufficient Data',
      colorClass: 'text-tx-muted',
      badgeClass: 'bg-surface-secondary text-tx-secondary border-border-primary',
      description: 'Requires at least 34 trading days (26-period slow EMA + 9-period signal smoothing).',
    };
  }

  const isBullish = histVal >= 0;
  const isAboveZero = macdVal >= 0;

  let label = '';
  let badgeClass = '';
  let description = '';

  if (isBullish) {
    label = isAboveZero ? 'Bullish (Above Zero)' : 'Bullish Convergence';
    badgeClass = 'bg-accent-green/10 text-accent-green border-accent-green/30';
    description = 'MACD line is above signal line, indicating positive short-term momentum.';
  } else {
    label = isAboveZero ? 'Bearish Divergence' : 'Bearish (Below Zero)';
    badgeClass = 'bg-accent-red/10 text-accent-red border-accent-red/30';
    description = 'MACD line is below signal line, indicating negative short-term momentum.';
  }

  return {
    status: isBullish ? 'BULLISH' : 'BEARISH',
    label,
    isAboveZero,
    histPositive: isBullish,
    badgeClass,
    description,
  };
}

/**
 * Classifies EMA alignment relative to current price.
 * 
 * @param {number|null} price
 * @param {number|null} ema20
 * @param {number|null} ema50
 * @param {number|null} ema200
 * @returns {object} EMA alignment description
 */
export function getEmaAlignment(price, ema20, ema50, ema200) {
  if (price == null) {
    return { status: 'UNKNOWN', label: 'Price Unavailable', badgeClass: 'bg-surface-secondary text-tx-muted' };
  }

  const validCount = [ema20, ema50, ema200].filter((v) => v !== null).length;
  if (validCount === 0) {
    return {
      status: 'INSUFFICIENT',
      label: 'Insufficient History for EMAs',
      badgeClass: 'bg-surface-secondary text-tx-muted',
      description: 'Insufficient historical bars to compute moving averages.',
    };
  }

  // If 20 and 50 are available
  if (ema20 != null && ema50 != null) {
    if (price > ema20 && ema20 > ema50) {
      const isBullStack = ema200 != null ? ema50 > ema200 : true;
      return {
        status: 'BULLISH_STACK',
        label: isBullStack ? 'Bullish Trend Alignment' : 'Short-term Bullish',
        badgeClass: 'bg-accent-green/10 text-accent-green border-accent-green/30',
        description: isBullStack
          ? 'Price is above EMA 20, 50, and 200, reflecting strong multi-horizon trend alignment.'
          : 'Price is above short-term EMAs (20 & 50).',
      };
    }

    if (price < ema20 && ema20 < ema50) {
      const isBearStack = ema200 != null ? ema50 < ema200 : true;
      return {
        status: 'BEARISH_STACK',
        label: isBearStack ? 'Bearish Trend Alignment' : 'Short-term Bearish',
        badgeClass: 'bg-accent-red/10 text-accent-red border-accent-red/30',
        description: isBearStack
          ? 'Price is below EMA 20, 50, and 200, reflecting downward multi-horizon alignment.'
          : 'Price is below short-term EMAs (20 & 50).',
      };
    }
  }

  return {
    status: 'MIXED',
    label: 'Mixed Moving Average Alignment',
    badgeClass: 'bg-surface-secondary text-tx-secondary border-border-primary',
    description: 'Price is consolidating around key moving averages with no dominant stack.',
  };
}
