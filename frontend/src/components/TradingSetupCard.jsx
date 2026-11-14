import React, { useState, useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Eye,
  Clock,
  Target,
  ShieldAlert,
  SlidersHorizontal,
  Info,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import RiskRewardVisualizer from './RiskRewardVisualizer';
import { calculateRiskReward } from '../utils/tradingSetup';
import { formatCurrency, formatPercent, formatRatio } from '../utils/formatters';

/**
 * DirectionBadge
 * Displays Bullish, Bearish, or Watch direction tag with theme-tailored colors.
 */
export const DirectionBadge = ({ direction, recommendation, className = '' }) => {
  const norm = (direction || recommendation || 'WATCH').toUpperCase();

  if (norm === 'BUY' || norm === 'BULLISH') {
    return (
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-accent-green/10 text-accent-green border border-accent-green/30 ${className}`}>
        <TrendingUp className="w-3.5 h-3.5 shrink-0" />
        Bullish Setup
      </span>
    );
  }
  if (norm === 'SELL' || norm === 'BEARISH') {
    return (
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-accent-red/10 text-accent-red border border-accent-red/30 ${className}`}>
        <TrendingDown className="w-3.5 h-3.5 shrink-0" />
        Bearish Setup
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-surface-secondary text-tx-secondary border border-border-primary ${className}`}>
      <Eye className="w-3.5 h-3.5 shrink-0" />
      Neutral / Watch
    </span>
  );
};

/**
 * TradingSetupCard
 * 
 * Comprehensive trading setup section implementing Phase 13 requirements:
 * - Entry price / entry zone
 * - Stop-loss price
 * - Target price
 * - Risk/reward ratio
 * - Expected holding period (3-8 weeks)
 * - Stock symbol and bullish/bearish setup direction
 * - Visual risk/reward representation
 * - Strict non-fabricated validation
 * - Clear compliance & educational disclaimer
 */
const TradingSetupCard = ({
  stock,
  className = '',
}) => {
  // Selected entry point within zone: 'mid' | 'low' | 'high'
  const [selectedEntryMode, setSelectedEntryMode] = useState('mid');

  const {
    symbol = '',
    companyName = '',
    currentPrice = null,
    recommendation = 'WATCH',
    entryLow = null,
    entryHigh = null,
    entryPrice: defaultEntryPrice = null,
    stopLoss = null,
    target = null,
    expectedHoldingWeeks = 5,
    signalValid = false,
  } = stock || {};

  const hasZone = entryLow != null && entryHigh != null && entryLow !== entryHigh;

  // Compute active entry price based on user selection or defaults
  const activeEntryPrice = useMemo(() => {
    if (hasZone) {
      if (selectedEntryMode === 'low') return Number(entryLow);
      if (selectedEntryMode === 'high') return Number(entryHigh);
      return (Number(entryLow) + Number(entryHigh)) / 2;
    }
    return defaultEntryPrice ?? currentPrice ?? null;
  }, [hasZone, selectedEntryMode, entryLow, entryHigh, defaultEntryPrice, currentPrice]);

  // Determine direction
  const direction = (recommendation === 'SELL' || recommendation === 'BEARISH') ? 'BEARISH' : 'BULLISH';

  // Calculate Risk / Reward dynamically from verified price data
  const calculationResult = useMemo(() => {
    return calculateRiskReward({
      entry: activeEntryPrice,
      stopLoss,
      target,
      direction,
    });
  }, [activeEntryPrice, stopLoss, target, direction]);

  if (!stock) return null;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Main Trading Setup Panel */}
      <div className="bg-surface rounded-2xl border border-border-primary p-5 sm:p-7 shadow-sm transition-colors">
        {/* Top Header: Symbol, Direction, Expected Horizon */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border-primary">
          <div>
            <div className="flex items-center flex-wrap gap-2.5 mb-1.5">
              <span className="font-heading font-bold text-2xl sm:text-3xl text-tx-primary tracking-tight">
                {symbol}
              </span>
              <DirectionBadge direction={direction} recommendation={recommendation} />
              {signalValid ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-medium rounded-md bg-accent-teal/10 text-accent-teal border border-accent-teal/20">
                  <CheckCircle2 className="w-3 h-3" />
                  Signal Qualified
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-medium rounded-md bg-surface-secondary text-tx-muted border border-border-primary">
                  <AlertCircle className="w-3 h-3" />
                  Preliminary Parameters
                </span>
              )}
            </div>
            <p className="text-xs sm:text-sm text-tx-secondary">
              {companyName} {currentPrice != null && `• Current Market: ${formatCurrency(currentPrice)}`}
            </p>
          </div>

          {/* Expected Holding Period (3–8 weeks) */}
          <div className="flex items-center gap-3 bg-surface-secondary/80 border border-border-primary rounded-xl px-4 py-2.5 self-start md:self-auto">
            <div className="p-2 rounded-lg bg-accent-teal/10 text-accent-teal shrink-0">
              <Clock className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-tx-muted">
                Holding Period
              </div>
              <div className="text-sm font-bold text-tx-primary font-heading">
                {expectedHoldingWeeks ? `${expectedHoldingWeeks} Weeks` : '3–8 Weeks'}{' '}
                <span className="text-xs font-normal text-tx-secondary">(Swing Horizon: 3–8 weeks)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Key Trade Parameters Grid (Entry Zone, Stop-Loss, Target, Risk/Reward) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 py-6 border-b border-border-primary">
          {/* 1. Entry Price / Zone */}
          <div className="bg-surface-secondary/50 rounded-xl p-4 border border-border-primary/80 transition-colors">
            <div className="flex items-center justify-between text-tx-secondary text-xs font-medium mb-1">
              <span>{hasZone ? 'ENTRY ZONE' : 'ENTRY PRICE'}</span>
              <span className="text-[10px] uppercase font-bold tracking-wider text-accent-teal">Trigger</span>
            </div>
            <div className="text-xl sm:text-2xl font-bold font-heading text-tx-primary font-mono truncate">
              {hasZone
                ? `${formatCurrency(entryLow, { decimals: 0 })} – ${formatCurrency(entryHigh, { decimals: 0 })}`
                : formatCurrency(activeEntryPrice)}
            </div>
            <div className="text-xs text-tx-secondary mt-1 truncate">
              {hasZone ? (
                <>Ref: <span className="font-mono text-tx-primary font-medium">{formatCurrency(activeEntryPrice)}</span> ({selectedEntryMode})</>
              ) : currentPrice != null ? (
                <>Market: <span className="font-mono">{formatCurrency(currentPrice)}</span></>
              ) : (
                'Algorithmic Entry'
              )}
            </div>
          </div>

          {/* 2. Stop-Loss Level */}
          <div className="bg-accent-red/5 rounded-xl p-4 border border-accent-red/20 transition-colors">
            <div className="flex items-center justify-between text-accent-red text-xs font-medium mb-1">
              <span>STOP-LOSS</span>
              <ShieldAlert className="w-3.5 h-3.5" />
            </div>
            <div className="text-xl sm:text-2xl font-bold font-heading text-tx-primary font-mono truncate">
              {formatCurrency(stopLoss)}
            </div>
            <div className="text-xs font-semibold text-accent-red mt-1">
              {calculationResult.isValid
                ? `-${formatCurrency(calculationResult.risk)} (-${formatPercent(calculationResult.riskPercent, { showSign: false })})`
                : 'Undefined stop-loss'}
            </div>
          </div>

          {/* 3. Target Level */}
          <div className="bg-accent-green/5 rounded-xl p-4 border border-accent-green/20 transition-colors">
            <div className="flex items-center justify-between text-accent-green text-xs font-medium mb-1">
              <span>TARGET PRICE</span>
              <Target className="w-3.5 h-3.5" />
            </div>
            <div className="text-xl sm:text-2xl font-bold font-heading text-tx-primary font-mono truncate">
              {formatCurrency(target)}
            </div>
            <div className="text-xs font-semibold text-accent-green mt-1">
              {calculationResult.isValid
                ? `+${formatCurrency(calculationResult.reward)} (+${formatPercent(calculationResult.rewardPercent, { showSign: false })})`
                : 'Undefined target'}
            </div>
          </div>

          {/* 4. Risk / Reward Ratio */}
          <div className="bg-surface-secondary/50 rounded-xl p-4 border border-border-primary/80 transition-colors">
            <div className="flex items-center justify-between text-tx-secondary text-xs font-medium mb-1">
              <span>RISK / REWARD</span>
              <span className="text-[10px] uppercase font-bold tracking-wider text-accent-teal">Calculated</span>
            </div>
            <div className="text-xl sm:text-2xl font-bold font-heading text-tx-primary font-mono truncate">
              {calculationResult.isValid
                ? formatRatio(calculationResult.riskRewardRatio)
                : '—'}
            </div>
            <div className="text-xs mt-1 font-medium">
              {calculationResult.isValid ? (
                calculationResult.riskRewardRatio >= 2.0 ? (
                  <span className="text-accent-green">≥ 2:1 Swing Standard</span>
                ) : (
                  <span className="text-accent-warning">Below 2:1 Standard</span>
                )
              ) : (
                <span className="text-tx-muted">Requires valid levels</span>
              )}
            </div>
          </div>
        </div>

        {/* Optional Entry Zone Sensitivity Selector (Only shown if entry zone exists) */}
        {hasZone && (
          <div className="pt-5 pb-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-tx-secondary">
              <SlidersHorizontal className="w-4 h-4 text-accent-teal" />
              <span>Evaluate execution within Entry Zone:</span>
            </div>
            <div className="inline-flex rounded-lg bg-surface-secondary p-1 border border-border-primary">
              <button
                type="button"
                onClick={() => setSelectedEntryMode('low')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  selectedEntryMode === 'low'
                    ? 'bg-surface text-tx-primary shadow-xs font-semibold'
                    : 'text-tx-secondary hover:text-tx-primary'
                }`}
              >
                Zone Low ({formatCurrency(entryLow, { decimals: 0 })})
              </button>
              <button
                type="button"
                onClick={() => setSelectedEntryMode('mid')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  selectedEntryMode === 'mid'
                    ? 'bg-surface text-tx-primary shadow-xs font-semibold'
                    : 'text-tx-secondary hover:text-tx-primary'
                }`}
              >
                Midpoint ({formatCurrency((Number(entryLow) + Number(entryHigh)) / 2, { decimals: 0 })})
              </button>
              <button
                type="button"
                onClick={() => setSelectedEntryMode('high')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  selectedEntryMode === 'high'
                    ? 'bg-surface text-tx-primary shadow-xs font-semibold'
                    : 'text-tx-secondary hover:text-tx-primary'
                }`}
              >
                Zone High ({formatCurrency(entryHigh, { decimals: 0 })})
              </button>
            </div>
          </div>
        )}

        {/* Risk / Reward Visualizer Section */}
        <div className="mt-6">
          <RiskRewardVisualizer
            calculationResult={calculationResult}
            entryZoneLow={entryLow}
            entryZoneHigh={entryHigh}
            currentPrice={currentPrice}
          />
        </div>

        {/* Setup Execution & Invalidation Rules */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-tx-secondary bg-surface-secondary/40 rounded-xl p-4 border border-border-primary/60">
          <div className="flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-accent-red shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-tx-primary">Invalidation Rule:</span>{' '}
              {stopLoss != null
                ? `Setup is invalidated if the stock closes below stop-loss at ${formatCurrency(stopLoss)} on a daily closing basis.`
                : 'A daily close below the technical support invalidates the setup.'}
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Target className="w-4 h-4 text-accent-green shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-tx-primary">Target Rule:</span>{' '}
              {target != null
                ? `Objective is targeted at ${formatCurrency(target)} within the 3–8 weeks swing holding horizon.`
                : 'Profit taking is planned at key resistance within 3–8 weeks.'}
            </div>
          </div>
        </div>

        {/* Required Disclaimer */}
        <div className="mt-6 p-4 rounded-xl bg-surface-secondary/70 border border-border-primary/80 flex items-start gap-3 text-xs text-tx-secondary">
          <Info className="w-4 h-4 text-tx-muted shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold text-tx-primary">Analytical Setup Only • Not Financial Advice:</span>{' '}
            All entry zones, stop-loss levels, and risk/reward calculations are algorithmically derived model estimates for swing trading strategy research.
            This is not a live trade recommendation, financial advice, or a guarantee of profit. Never risk capital without independent verification and appropriate position sizing.
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingSetupCard;
