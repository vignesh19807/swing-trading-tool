/**
 * @file formatters.js
 * @description Pure formatting utility functions for currency, percentages, ratios, and scores.
 */

/**
 * Formats a numeric value into INR currency (e.g., ₹3,520.00).
 * 
 * @param {number|string|null|undefined} value 
 * @param {object} [options]
 * @param {number} [options.decimals=2]
 * @param {boolean} [options.compact=false]
 * @returns {string} Formatted string or '—' if invalid
 */
export function formatCurrency(value, { decimals = 2, compact = false } = {}) {
  if (value == null || value === '' || isNaN(Number(value))) {
    return '—';
  }
  const num = Number(value);
  if (compact && Math.abs(num) >= 10000000) {
    return `₹${(num / 10000000).toFixed(2)} Cr`;
  }
  if (compact && Math.abs(num) >= 100000) {
    return `₹${(num / 100000).toFixed(2)} L`;
  }
  return `₹${num.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

/**
 * Formats a numeric value into a percentage with sign (e.g., +5.20%, -2.15%).
 * 
 * @param {number|string|null|undefined} value 
 * @param {object} [options]
 * @param {boolean} [options.showSign=true]
 * @param {number} [options.decimals=2]
 * @returns {string}
 */
export function formatPercent(value, { showSign = true, decimals = 2 } = {}) {
  if (value == null || value === '' || isNaN(Number(value))) {
    return '—';
  }
  const num = Number(value);
  const sign = showSign && num > 0 ? '+' : '';
  return `${sign}${num.toFixed(decimals)}%`;
}

/**
 * Formats a risk-to-reward ratio (e.g., 2.10:1 or 2.1x).
 * 
 * @param {number|string|null|undefined} value 
 * @param {object} [options]
 * @param {string} [options.format='ratio'] - 'ratio' for '2.10:1', 'multiplier' for '2.1x'
 * @param {number} [options.decimals=2]
 * @returns {string}
 */
export function formatRatio(value, { format = 'ratio', decimals = 2 } = {}) {
  if (value == null || value === '' || isNaN(Number(value)) || Number(value) <= 0) {
    return '—';
  }
  const num = Number(value);
  if (format === 'multiplier') {
    return `${num.toFixed(decimals)}x`;
  }
  return `${num.toFixed(decimals)} : 1`;
}

/**
 * Formats a score out of 100.
 * 
 * @param {number|string|null|undefined} score 
 * @param {number} [decimals=1]
 * @returns {string}
 */
export function formatScore(score, decimals = 1) {
  if (score == null || score === '' || isNaN(Number(score))) {
    return '—';
  }
  return Number(score).toFixed(decimals);
}
