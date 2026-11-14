import React from 'react';
import { Target, ShieldAlert, Scale, AlertTriangle, ArrowUp, ArrowDown } from 'lucide-react';
import { formatCurrency, formatPercent } from '../utils/formatters';

/**
 * RiskRewardVisualizer
 * 
 * Renders an intuitive visual comparison of potential downside vs potential upside,
 * key price levels (Target, Entry, Stop Loss), and the risk/reward ratio.
 * 
 * Supports light & dark themes, responsive desktop & mobile layouts,
 * and robust graceful handling of missing or invalid price parameters.
 */
const RiskRewardVisualizer = ({
  calculationResult,
  entryZoneLow = null,
  entryZoneHigh = null,
  currentPrice = null,
  className = '',
}) => {
  const {
    isValid,
    isMissing,
    errorMessage,
    direction = 'BULLISH',
    entry,
    stopLoss,
    target,
    risk,
    reward,
    riskPercent,
    rewardPercent,
    riskRewardRatio,
    quality,
    riskSharePercent = 50,
    rewardSharePercent = 50,
  } = calculationResult || {};

  const isBearish = direction === 'BEARISH';

  // If calculation is invalid or missing required levels
  if (!isValid) {
    return (
      <div className={`rounded-xl border border-border-primary bg-surface p-5 sm:p-6 transition-colors ${className}`}>
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-accent-warning/10 text-accent-warning shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-heading font-semibold text-sm text-tx-primary mb-1">
              {isMissing ? 'Setup Parameters Incomplete' : 'Invalid Price Structure'}
            </h4>
            <p className="text-xs text-tx-secondary leading-relaxed mb-4">
              {errorMessage || 'A valid risk/reward ratio requires defined entry, stop-loss, and target levels.'}
            </p>

            {/* Partial levels display */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-border-primary">
              <div className="bg-surface-secondary/70 p-3 rounded-lg border border-border-primary/60">
                <div className="text-[11px] font-semibold tracking-wider uppercase text-tx-muted mb-0.5">Target Level</div>
                <div className="font-mono text-sm font-semibold text-tx-primary">
                  {target != null ? formatCurrency(target) : 'Not defined'}
                </div>
              </div>
              <div className="bg-surface-secondary/70 p-3 rounded-lg border border-border-primary/60">
                <div className="text-[11px] font-semibold tracking-wider uppercase text-tx-muted mb-0.5">Entry Level</div>
                <div className="font-mono text-sm font-semibold text-tx-primary">
                  {entry != null ? formatCurrency(entry) : 'Not defined'}
                </div>
              </div>
              <div className="bg-surface-secondary/70 p-3 rounded-lg border border-border-primary/60">
                <div className="text-[11px] font-semibold tracking-wider uppercase text-tx-muted mb-0.5">Stop-Loss Level</div>
                <div className="font-mono text-sm font-semibold text-tx-primary">
                  {stopLoss != null ? formatCurrency(stopLoss) : 'Not defined'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Quality badge helper
  const getQualityBadge = () => {
    if (quality === 'favourable') {
      return {
        label: 'Favourable (≥ 2.0 : 1)',
        badgeClass: 'bg-accent-green/10 text-accent-green border-accent-green/30',
        textClass: 'text-accent-green',
        summary: 'Exceeds the 2.0:1 institutional swing trading benchmark.',
      };
    }
    if (quality === 'acceptable') {
      return {
        label: 'Acceptable (1.5 – 2.0 : 1)',
        badgeClass: 'bg-accent-warning/10 text-accent-warning border-accent-warning/30',
        textClass: 'text-accent-warning',
        summary: 'Acceptable margin of safety, but closer to minimum swing viability.',
      };
    }
    return {
      label: 'Sub-optimal (< 1.5 : 1)',
      badgeClass: 'bg-accent-red/10 text-accent-red border-accent-red/30',
      textClass: 'text-accent-red',
      summary: 'Potential upside may not adequately compensate for downside risk.',
    };
  };

  const badgeInfo = getQualityBadge();

  return (
    <div className={`rounded-xl border border-border-primary bg-surface p-5 sm:p-6 transition-colors shadow-sm ${className}`}>
      {/* Header: Ratio Display & Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-border-primary">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Scale className="w-4 h-4 text-accent-teal" />
            <span className="text-xs font-semibold tracking-wider uppercase text-tx-secondary">
              Risk / Reward Evaluation
            </span>
          </div>
          <p className="text-xs text-tx-secondary">
            {badgeInfo.summary}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[11px] uppercase tracking-wider text-tx-muted font-medium">Calculated Ratio</div>
            <div className="font-heading font-bold text-2xl sm:text-3xl text-tx-primary tracking-tight">
              {riskRewardRatio != null ? `${riskRewardRatio.toFixed(2)} : 1` : '—'}
            </div>
          </div>
          <div className={`px-2.5 py-1 text-xs font-semibold rounded-md border ${badgeInfo.badgeClass}`}>
            {badgeInfo.label}
          </div>
        </div>
      </div>

      {/* Proportional Split Bar (Risk vs Reward) */}
      <div className="my-6">
        <div className="flex justify-between items-center text-xs font-medium mb-2">
          <span className="inline-flex items-center gap-1 text-accent-red font-semibold">
            <ArrowDown className="w-3.5 h-3.5" />
            Downside Risk: -{formatCurrency(risk)} ({formatPercent(riskPercent, { showSign: false })})
          </span>
          <span className="inline-flex items-center gap-1 text-accent-green font-semibold">
            Upside Reward: +{formatCurrency(reward)} ({formatPercent(rewardPercent, { showSign: false })})
            <ArrowUp className="w-3.5 h-3.5" />
          </span>
        </div>

        <div className="h-3 w-full bg-surface-secondary rounded-full overflow-hidden flex p-0.5 border border-border-primary">
          <div
            className="h-full bg-accent-red rounded-l-full transition-all duration-500 relative group"
            style={{ width: `${Math.max(riskSharePercent, 8)}%` }}
            title={`Risk: ${riskSharePercent.toFixed(1)}% of total spread`}
          ></div>
          <div
            className="h-full bg-accent-green rounded-r-full transition-all duration-500 relative group"
            style={{ width: `${Math.max(rewardSharePercent, 8)}%` }}
            title={`Reward: ${rewardSharePercent.toFixed(1)}% of total spread`}
          ></div>
        </div>

        <div className="flex justify-between text-[11px] text-tx-muted mt-1.5 px-0.5 font-mono">
          <span>{riskSharePercent.toFixed(0)}% Risk Share</span>
          <span className="font-sans font-semibold text-tx-secondary">Pivot at Entry</span>
          <span>{rewardSharePercent.toFixed(0)}% Reward Share</span>
        </div>
      </div>

      {/* Vertical Price Ladder: Target -> Entry -> Stop Loss */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
        {/* 1. Target Level Card */}
        <div className="bg-accent-green/5 border border-accent-green/20 rounded-xl p-4 flex flex-col justify-between transition-colors">
          <div className="flex items-start justify-between mb-2">
            <div>
              <span className="text-[11px] font-bold tracking-wider uppercase text-accent-green block">
                {isBearish ? 'Downside Target' : 'Target Objective'}
              </span>
              <span className="text-xs text-tx-muted">Take-profit level</span>
            </div>
            <div className="p-1.5 rounded-lg bg-accent-green/10 text-accent-green">
              <Target className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="font-heading font-bold text-xl sm:text-2xl text-tx-primary tracking-tight font-mono">
              {formatCurrency(target)}
            </div>
            <div className="text-xs font-semibold text-accent-green flex items-center gap-1 mt-1">
              <span>+{formatCurrency(reward)}</span>
              <span>({formatPercent(rewardPercent, { showSign: true })})</span>
            </div>
          </div>
        </div>

        {/* 2. Entry Level / Zone Card */}
        <div className="bg-accent-teal/5 border border-accent-teal/20 rounded-xl p-4 flex flex-col justify-between transition-colors">
          <div className="flex items-start justify-between mb-2">
            <div>
              <span className="text-[11px] font-bold tracking-wider uppercase text-accent-teal block">
                {entryZoneLow != null && entryZoneHigh != null ? 'Entry Zone' : 'Planned Entry'}
              </span>
              <span className="text-xs text-tx-muted">Execution price pivot</span>
            </div>
            <div className="p-1.5 rounded-lg bg-accent-teal/10 text-accent-teal font-mono text-xs font-bold">
              REF
            </div>
          </div>
          <div>
            <div className="font-heading font-bold text-xl sm:text-2xl text-tx-primary tracking-tight font-mono">
              {formatCurrency(entry)}
            </div>
            {entryZoneLow != null && entryZoneHigh != null ? (
              <div className="text-xs text-tx-secondary mt-1 truncate">
                Zone: <span className="font-mono font-medium text-tx-primary">{formatCurrency(entryZoneLow)}</span> – <span className="font-mono font-medium text-tx-primary">{formatCurrency(entryZoneHigh)}</span>
              </div>
            ) : currentPrice != null ? (
              <div className="text-xs text-tx-secondary mt-1">
                Market: <span className="font-mono font-medium text-tx-primary">{formatCurrency(currentPrice)}</span>
              </div>
            ) : (
              <div className="text-xs text-tx-secondary mt-1">Reference price</div>
            )}
          </div>
        </div>

        {/* 3. Stop-Loss Level Card */}
        <div className="bg-accent-red/5 border border-accent-red/20 rounded-xl p-4 flex flex-col justify-between transition-colors">
          <div className="flex items-start justify-between mb-2">
            <div>
              <span className="text-[11px] font-bold tracking-wider uppercase text-accent-red block">
                Stop-Loss Level
              </span>
              <span className="text-xs text-tx-muted">Capital preservation floor</span>
            </div>
            <div className="p-1.5 rounded-lg bg-accent-red/10 text-accent-red">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="font-heading font-bold text-xl sm:text-2xl text-tx-primary tracking-tight font-mono">
              {formatCurrency(stopLoss)}
            </div>
            <div className="text-xs font-semibold text-accent-red flex items-center gap-1 mt-1">
              <span>-{formatCurrency(risk)}</span>
              <span>(-{formatPercent(riskPercent, { showSign: false })})</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskRewardVisualizer;
