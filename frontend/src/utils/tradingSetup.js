/**
 * @file tradingSetup.js
 * @description Domain logic for trading setups, risk/reward calculations, and stock intelligence data normalization.
 */

/**
 * Normalizes disparate backend/mock stock schemas into a unified, reliable shape.
 * Handles both flat schemas (mockStock, mockOpportunities) and nested schemas (stock_intelligence contract).
 * 
 * @param {object|null} raw 
 * @returns {object|null}
 */
export function normalizeStockData(raw) {
  if (!raw || typeof raw !== 'object') return null;

  const symbol = raw.symbol || raw.identity?.symbol || 'UNKNOWN';
  const companyName = raw.company_name || raw.identity?.company_name || symbol;
  const sector = raw.sector || raw.identity?.sector || '—';
  const industry = raw.industry || raw.identity?.industry || '—';
  const currentPrice = raw.current_price ?? raw.market_price ?? raw.close ?? null;
  const priceChangePercent = raw.price_change_percent ?? raw.change_percent ?? null;

  const rawRec = (
    raw.recommendation ||
    raw.decision_result?.recommendation ||
    raw.signal_result?.recommendation ||
    'WATCH'
  ).toUpperCase();

  let recommendation = 'WATCH';
  if (rawRec === 'BUY' || rawRec === 'BULLISH') recommendation = 'BUY';
  else if (rawRec === 'SELL' || rawRec === 'BEARISH') recommendation = 'SELL';

  // Entry parameters
  const entryLow = raw.entry_zone_low ?? raw.signal_result?.entry_lower ?? null;
  const entryHigh = raw.entry_zone_high ?? raw.signal_result?.entry_upper ?? null;

  let entryPrice = raw.entry_price ?? null;
  if (entryPrice == null) {
    if (entryLow != null && entryHigh != null) {
      entryPrice = (Number(entryLow) + Number(entryHigh)) / 2;
    } else if (currentPrice != null) {
      entryPrice = Number(currentPrice);
    }
  }

  // Stop loss and target
  const stopLoss = raw.stop_loss ?? raw.signal_result?.stop_loss ?? null;
  const target = raw.target ?? raw.signal_result?.target ?? null;

  // Holding period (swing default is 3-8 weeks)
  const expectedHoldingWeeks = raw.expected_holding_weeks ?? raw.signal_result?.expected_holding_weeks ?? 5;

  // Pre-supplied risk reward (if provided by backend)
  const rawRiskReward = raw.risk_reward ?? raw.signal_result?.risk_reward_ratio ?? null;

  // Multi-factor scores
  const opportunityScore = raw.opportunity_score ?? raw.decision_result?.opportunity_score ?? null;
  const technicalScore = raw.technical_score ?? raw.decision_result?.technical_score ?? null;
  const financialScore = raw.financial_score ?? raw.decision_result?.financial_score ?? null;
  const momentumScore = raw.momentum_score ?? raw.decision_result?.momentum_score ?? null;
  const riskScore = raw.risk_score ?? raw.trade_quality?.risk_score ?? null;

  // Factors and qualitative breakdown
  let bullishFactors = [];
  if (Array.isArray(raw.bullish_factors)) {
    bullishFactors = raw.bullish_factors;
  } else if (Array.isArray(raw.structured_explanation?.explanation?.positive_factors)) {
    bullishFactors = raw.structured_explanation.explanation.positive_factors.map((f) =>
      typeof f === 'string'
        ? f
        : `${f.category ? f.category + ': ' : ''}${f.interpretation || f.metric || ''}`
    );
  }

  let riskFactors = [];
  if (Array.isArray(raw.risk_factors)) {
    riskFactors = raw.risk_factors;
  } else if (Array.isArray(raw.trade_quality?.risk_flags)) {
    riskFactors = raw.trade_quality.risk_flags;
  } else if (Array.isArray(raw.structured_explanation?.explanation?.risk_factors)) {
    riskFactors = raw.structured_explanation.explanation.risk_factors.map((f) =>
      typeof f === 'string'
        ? f
        : `${f.category ? f.category + ': ' : ''}${f.interpretation || f.metric || ''}`
    );
  }

  const explanation =
    raw.explanation ||
    raw.structured_explanation?.explanation?.summary ||
    null;

  const signalValid =
    raw.signal_result?.signal_valid ??
    (recommendation === 'BUY' && stopLoss != null && target != null);

  return {
    symbol,
    companyName,
    sector,
    industry,
    currentPrice: currentPrice != null ? Number(currentPrice) : null,
    priceChangePercent: priceChangePercent != null ? Number(priceChangePercent) : null,
    recommendation,
    entryLow: entryLow != null ? Number(entryLow) : null,
    entryHigh: entryHigh != null ? Number(entryHigh) : null,
    entryPrice: entryPrice != null ? Number(entryPrice) : null,
    stopLoss: stopLoss != null ? Number(stopLoss) : null,
    target: target != null ? Number(target) : null,
    expectedHoldingWeeks: Number(expectedHoldingWeeks) || 5,
    rawRiskReward: rawRiskReward != null ? Number(rawRiskReward) : null,
    opportunityScore: opportunityScore != null ? Number(opportunityScore) : null,
    technicalScore: technicalScore != null ? Number(technicalScore) : null,
    financialScore: financialScore != null ? Number(financialScore) : null,
    momentumScore: momentumScore != null ? Number(momentumScore) : null,
    riskScore: riskScore != null ? Number(riskScore) : null,
    bullishFactors,
    riskFactors,
    explanation,
    signalValid,
    evaluationDate: raw.evaluation_date || null,
  };
}

/**
 * Calculates Risk, Reward, and Risk/Reward Ratio strictly according to setup rules.
 * 
 * Long Setup:
 *   Risk = Entry − Stop Loss
 *   Reward = Target − Entry
 *   Risk/Reward = Reward ÷ Risk
 * 
 * Short Setup:
 *   Risk = Stop Loss − Entry
 *   Reward = Entry − Target
 *   Risk/Reward = Reward ÷ Risk
 * 
 * Validates inputs to ensure no fabricated calculations, division by zero, or negative spreads.
 * 
 * @param {object} params
 * @param {number|null} params.entry
 * @param {number|null} params.stopLoss
 * @param {number|null} params.target
 * @param {'BULLISH'|'BEARISH'|'BUY'|'SELL'|'WATCH'} [params.direction='BULLISH']
 * @returns {object} Calculated result and status metadata
 */
export function calculateRiskReward({
  entry,
  stopLoss,
  target,
  direction = 'BULLISH',
}) {
  const isBearish = direction === 'BEARISH' || direction === 'SELL';
  const normDirection = isBearish ? 'BEARISH' : 'BULLISH';

  const numEntry = entry != null ? Number(entry) : NaN;
  const numStop = stopLoss != null ? Number(stopLoss) : NaN;
  const numTarget = target != null ? Number(target) : NaN;

  const isEntryValid = !isNaN(numEntry) && numEntry > 0;
  const isStopValid = !isNaN(numStop) && numStop > 0;
  const isTargetValid = !isNaN(numTarget) && numTarget > 0;

  if (!isEntryValid || !isStopValid || !isTargetValid) {
    const missingFields = [];
    if (!isEntryValid) missingFields.push('Entry Price');
    if (!isStopValid) missingFields.push('Stop-Loss');
    if (!isTargetValid) missingFields.push('Target Price');

    return {
      isValid: false,
      isMissing: true,
      errorMessage: `Setup incomplete: Missing ${missingFields.join(', ')}.`,
      direction: normDirection,
      entry: isEntryValid ? numEntry : null,
      stopLoss: isStopValid ? numStop : null,
      target: isTargetValid ? numTarget : null,
      risk: null,
      reward: null,
      riskPercent: null,
      rewardPercent: null,
      riskRewardRatio: null,
      quality: 'invalid',
      riskSharePercent: 50,
      rewardSharePercent: 50,
    };
  }

  let risk = 0;
  let reward = 0;

  if (!isBearish) {
    // LONG / BULLISH:
    risk = numEntry - numStop;
    reward = numTarget - numEntry;

    if (numStop >= numEntry) {
      return {
        isValid: false,
        isMissing: false,
        errorMessage: `Invalid long setup: Stop-loss (₹${numStop.toLocaleString('en-IN')}) must be below Entry price (₹${numEntry.toLocaleString('en-IN')}).`,
        direction: normDirection,
        entry: numEntry,
        stopLoss: numStop,
        target: numTarget,
        risk: null,
        reward: null,
        riskPercent: null,
        rewardPercent: null,
        riskRewardRatio: null,
        quality: 'invalid',
        riskSharePercent: 50,
        rewardSharePercent: 50,
      };
    }

    if (numTarget <= numEntry) {
      return {
        isValid: false,
        isMissing: false,
        errorMessage: `Invalid long setup: Target (₹${numTarget.toLocaleString('en-IN')}) must be above Entry price (₹${numEntry.toLocaleString('en-IN')}).`,
        direction: normDirection,
        entry: numEntry,
        stopLoss: numStop,
        target: numTarget,
        risk: null,
        reward: null,
        riskPercent: null,
        rewardPercent: null,
        riskRewardRatio: null,
        quality: 'invalid',
        riskSharePercent: 50,
        rewardSharePercent: 50,
      };
    }
  } else {
    // SHORT / BEARISH:
    risk = numStop - numEntry;
    reward = numEntry - numTarget;

    if (numStop <= numEntry) {
      return {
        isValid: false,
        isMissing: false,
        errorMessage: `Invalid short setup: Stop-loss (₹${numStop.toLocaleString('en-IN')}) must be above Entry price (₹${numEntry.toLocaleString('en-IN')}).`,
        direction: normDirection,
        entry: numEntry,
        stopLoss: numStop,
        target: numTarget,
        risk: null,
        reward: null,
        riskPercent: null,
        rewardPercent: null,
        riskRewardRatio: null,
        quality: 'invalid',
        riskSharePercent: 50,
        rewardSharePercent: 50,
      };
    }

    if (numTarget >= numEntry) {
      return {
        isValid: false,
        isMissing: false,
        errorMessage: `Invalid short setup: Target (₹${numTarget.toLocaleString('en-IN')}) must be below Entry price (₹${numEntry.toLocaleString('en-IN')}).`,
        direction: normDirection,
        entry: numEntry,
        stopLoss: numStop,
        target: numTarget,
        risk: null,
        reward: null,
        riskPercent: null,
        rewardPercent: null,
        riskRewardRatio: null,
        quality: 'invalid',
        riskSharePercent: 50,
        rewardSharePercent: 50,
      };
    }
  }

  if (risk <= 0) {
    return {
      isValid: false,
      isMissing: false,
      errorMessage: 'Calculated risk is zero or negative. A valid risk/reward ratio cannot be computed.',
      direction: normDirection,
      entry: numEntry,
      stopLoss: numStop,
      target: numTarget,
      risk: null,
      reward: null,
      riskPercent: null,
      rewardPercent: null,
      riskRewardRatio: null,
      quality: 'invalid',
      riskSharePercent: 50,
      rewardSharePercent: 50,
    };
  }

  const ratio = reward / risk;
  const riskPercent = (risk / numEntry) * 100;
  const rewardPercent = (reward / numEntry) * 100;

  let quality = 'suboptimal';
  if (ratio >= 2.0) {
    quality = 'favourable'; // Swing target benchmark >= 2.0:1
  } else if (ratio >= 1.5) {
    quality = 'acceptable'; // Acceptable setup >= 1.5:1
  }

  const totalSpread = risk + reward;
  const riskSharePercent = totalSpread > 0 ? (risk / totalSpread) * 100 : 50;
  const rewardSharePercent = totalSpread > 0 ? (reward / totalSpread) * 100 : 50;

  return {
    isValid: true,
    isMissing: false,
    errorMessage: null,
    direction: normDirection,
    entry: numEntry,
    stopLoss: numStop,
    target: numTarget,
    risk,
    reward,
    riskPercent,
    rewardPercent,
    riskRewardRatio: ratio,
    quality,
    riskSharePercent,
    rewardSharePercent,
  };
}
