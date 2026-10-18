/**
 * @file chartHelpers.js
 * @description Coordinate transformation, range filtering, and scaling math for SVG price charts.
 */

/**
 * Standard trading time-range definitions (trading days approximation).
 */
export const TIME_RANGES = [
  { key: '1W', label: '1W', tradingDays: 5, description: '1 Week' },
  { key: '1M', label: '1M', tradingDays: 21, description: '1 Month' },
  { key: '3M', label: '3M', tradingDays: 63, description: '3 Months' },
  { key: '6M', label: '6M', tradingDays: 126, description: '6 Months' },
  { key: '1Y', label: '1Y', tradingDays: 252, description: '1 Year' },
];

/**
 * Evaluates whether a given time range is supported by the data length.
 * 
 * @param {Array<object>} data
 * @param {string} rangeKey
 * @returns {boolean}
 */
export function isRangeSupported(data, rangeKey) {
  if (!Array.isArray(data) || data.length === 0) return false;
  const def = TIME_RANGES.find((r) => r.key === rangeKey);
  if (!def) return false;
  
  // 1W requires at least 3 points
  if (def.key === '1W') return data.length >= 2;
  // 1M requires > 5 points
  if (def.key === '1M') return data.length > 5;
  // 3M requires > 21 points
  if (def.key === '3M') return data.length > 21;
  // 6M requires > 63 points
  if (def.key === '6M') return data.length > 63;
  // 1Y requires > 126 points
  if (def.key === '1Y') return data.length > 126;

  return data.length >= def.tradingDays;
}

/**
 * Filters the historical dataset to the specified range.
 * 
 * @param {Array<object>} data
 * @param {string} rangeKey
 * @returns {Array<object>}
 */
export function filterHistoryByRange(data, rangeKey) {
  if (!Array.isArray(data) || data.length === 0) return [];
  const def = TIME_RANGES.find((r) => r.key === rangeKey);
  if (!def) return data;

  const count = def.tradingDays;
  if (data.length <= count) return data;
  return data.slice(-count);
}

/**
 * Validates whether the dataset contains complete OHLC and Volume fields.
 * 
 * @param {Array<object>} data
 * @returns {{hasOHLC: boolean, hasVolume: boolean, validCount: number}}
 */
export function validateOHLC(data) {
  if (!Array.isArray(data) || data.length === 0) {
    return { hasOHLC: false, hasVolume: false, validCount: 0 };
  }

  let ohlcCount = 0;
  let volumeCount = 0;

  for (const item of data) {
    if (
      item.open != null && !isNaN(Number(item.open)) &&
      item.high != null && !isNaN(Number(item.high)) &&
      item.low != null && !isNaN(Number(item.low)) &&
      item.close != null && !isNaN(Number(item.close))
    ) {
      ohlcCount++;
    }
    if (item.volume != null && !isNaN(Number(item.volume)) && Number(item.volume) > 0) {
      volumeCount++;
    }
  }

  return {
    hasOHLC: ohlcCount >= Math.min(data.length, 3) && (ohlcCount / data.length) >= 0.8,
    hasVolume: volumeCount > 0,
    validCount: ohlcCount,
  };
}

/**
 * Generates nice round tick steps for price axes.
 */
function getNiceTicks(min, max, targetCount = 5) {
  const span = max - min;
  if (span <= 0) return [min];

  const rawStep = span / targetCount;
  const power = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const normalizedStep = rawStep / power;

  let step;
  if (normalizedStep < 1.5) step = 1 * power;
  else if (normalizedStep < 3) step = 2 * power;
  else if (normalizedStep < 7) step = 5 * power;
  else step = 10 * power;

  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;

  const ticks = [];
  for (let val = start; val <= end + step * 0.001; val += step) {
    if (val >= min - step * 0.1 && val <= max + step * 0.1) {
      ticks.push(Math.round(val * 100) / 100);
    }
  }
  return ticks.length >= 2 ? ticks : [min, max];
}

/**
 * Computes coordinate scale mappings for the price chart and volume pane.
 * 
 * @param {object} params
 * @param {Array<object>} params.data - Filtered chart data
 * @param {number} params.width - SVG width in pixels
 * @param {number} params.height - SVG height in pixels
 * @param {object} params.margin - Margins {top, right, bottom, left}
 * @param {object} [params.setupLevels] - Optional {entry, stopLoss, target}
 * @param {boolean} [params.hasVolume=true]
 * @returns {object} Scale functions, boundaries, and ticks
 */
export function calculateScales({
  data,
  width,
  height,
  margin = { top: 20, right: 65, bottom: 40, left: 16 },
  setupLevels = null,
  hasVolume = true,
  extraPrices = [],
}) {
  if (!Array.isArray(data) || data.length === 0) {
    return null;
  }

  const chartWidth = Math.max(width - margin.left - margin.right, 50);
  const chartHeight = Math.max(height - margin.top - margin.bottom, 50);

  // Split height: Price area gets top ~75%, Volume area gets bottom ~25%
  const volumeHeight = hasVolume ? Math.min(Math.floor(chartHeight * 0.22), 70) : 0;
  const priceHeight = chartHeight - volumeHeight - (hasVolume ? 12 : 0);

  // Price boundaries
  let minPrice = Infinity;
  let maxPrice = -Infinity;
  let maxVolume = 0;

  for (const d of data) {
    const high = d.high != null && !isNaN(d.high) ? Number(d.high) : Number(d.close);
    const low = d.low != null && !isNaN(d.low) ? Number(d.low) : Number(d.close);
    const vol = d.volume != null && !isNaN(d.volume) ? Number(d.volume) : 0;

    if (high > maxPrice) maxPrice = high;
    if (low < minPrice) minPrice = low;
    if (vol > maxVolume) maxVolume = vol;
  }

  // Include extra prices (such as enabled EMA overlays)
  if (Array.isArray(extraPrices)) {
    for (const val of extraPrices) {
      if (val != null && !isNaN(val) && Number(val) > 0) {
        const num = Number(val);
        if (num > maxPrice) maxPrice = num;
        if (num < minPrice) minPrice = num;
      }
    }
  }

  // Include setup levels in price range if they are within a reasonable buffer (<= 25% from data min/max)
  if (setupLevels) {
    const { target, stopLoss, entry } = setupLevels;
    const candidates = [target, stopLoss, entry].filter((v) => v != null && !isNaN(v) && Number(v) > 0);
    for (const val of candidates) {
      const num = Number(val);
      if (num > maxPrice && num <= maxPrice * 1.25) maxPrice = num;
      if (num < minPrice && num >= minPrice * 0.75) minPrice = num;
    }
  }

  if (minPrice === Infinity || maxPrice === -Infinity) {
    minPrice = 100;
    maxPrice = 200;
  }

  // Add 3% vertical breathing room
  const pricePadding = (maxPrice - minPrice) * 0.04 || 5;
  const scaledMin = minPrice - pricePadding;
  const scaledMax = maxPrice + pricePadding;
  const priceRange = scaledMax - scaledMin || 1;

  // Coordinate functions
  const getYForPrice = (price) => {
    if (price == null || isNaN(price)) return 0;
    const normalized = (Number(price) - scaledMin) / priceRange;
    return margin.top + (1 - normalized) * priceHeight;
  };

  const getPriceForY = (y) => {
    const relY = y - margin.top;
    const normalized = 1 - (relY / priceHeight);
    return scaledMin + normalized * priceRange;
  };

  // Volume coordinate function
  const volumeBaselineY = margin.top + priceHeight + (hasVolume ? 12 : 0) + volumeHeight;
  const getYForVolume = (volume) => {
    if (!hasVolume || !maxVolume || volume == null) return volumeBaselineY;
    const norm = Math.min(Math.max(Number(volume) / maxVolume, 0), 1);
    return volumeBaselineY - norm * volumeHeight;
  };

  // X-coordinate mapping per data index
  const candleCount = data.length;
  const stepX = candleCount > 1 ? chartWidth / (candleCount - 1) : chartWidth;
  const candleWidth = Math.max(Math.min(stepX * 0.72, 14), 2);

  const getXForIndex = (index) => {
    if (candleCount <= 1) return margin.left + chartWidth / 2;
    return margin.left + index * stepX;
  };

  // Generate Y price ticks
  const priceTicks = getNiceTicks(scaledMin, scaledMax, 5);

  // Generate X date ticks (4 to 6 evenly spaced date markers)
  const xTickIndices = [];
  const targetXTicks = Math.min(Math.max(Math.floor(chartWidth / 100), 2), 6);
  const stepIdx = Math.max(Math.floor(candleCount / (targetXTicks - 1)), 1);

  for (let i = 0; i < candleCount; i += stepIdx) {
    xTickIndices.push(i);
  }
  if (xTickIndices[xTickIndices.length - 1] !== candleCount - 1) {
    xTickIndices.push(candleCount - 1);
  }

  return {
    margin,
    chartWidth,
    chartHeight,
    priceHeight,
    volumeHeight,
    volumeBaselineY,
    minPrice: scaledMin,
    maxPrice: scaledMax,
    maxVolume,
    stepX,
    candleWidth,
    getYForPrice,
    getPriceForY,
    getYForVolume,
    getXForIndex,
    priceTicks,
    xTickIndices,
  };
}

/**
 * Formats date label for X-axis display.
 * 
 * @param {string} dateStr - YYYY-MM-DD
 * @returns {string}
 */
export function formatXAxisDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-IN', {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Formats full date for tooltips.
 * 
 * @param {string} dateStr - YYYY-MM-DD
 * @returns {string}
 */
export function formatTooltipDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-IN', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}
