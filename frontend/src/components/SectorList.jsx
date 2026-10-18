import React from 'react';
import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LoadingState, ErrorState, EmptyState } from './StateComponents';

const SectorRow = ({ sector }) => {
  const rs = sector.relative_strength_vs_nifty != null ? Number(sector.relative_strength_vs_nifty) : null;
  const perf21 = sector.performance_21d != null ? Number(sector.performance_21d) : null;

  let label = 'In-line';
  let badgeColor = 'bg-accent-warning/10 text-accent-warning border-accent-warning/20';
  let barColor = 'bg-accent-warning';

  if (rs != null) {
    if (rs >= 1.05) {
      label = 'Outperforming';
      badgeColor = 'bg-accent-green/10 text-accent-green border-accent-green/20';
      barColor = 'bg-accent-green';
    } else if (rs <= 0.95) {
      label = 'Lagging';
      badgeColor = 'bg-accent-red/10 text-accent-red border-accent-red/20';
      barColor = 'bg-accent-red';
    }
  }

  // Visual bar normalized around benchmark ratio 1.00 (range 0.8 to 1.2 mapped to 15% to 95%)
  const barWidth = rs != null
    ? Math.min(Math.max(((rs - 0.8) / (1.2 - 0.8)) * 100, 15), 100)
    : 50;

  return (
    <div className="space-y-1.5 pb-3 border-b border-border-primary/50 last:border-0 last:pb-0">
      <div className="flex justify-between items-start">
        <div>
          <span className="font-semibold text-tx-primary text-sm">{sector.sector}</span>
          {sector.stock_count != null && (
            <span className="text-xs text-tx-secondary ml-1.5 font-normal">
              ({sector.stock_count} stocks)
            </span>
          )}
        </div>
        <div className="text-right">
          <span className={`text-xs px-2 py-0.5 rounded border font-medium ${badgeColor}`}>
            {label}
          </span>
        </div>
      </div>

      <div className="flex justify-between items-center text-xs text-tx-secondary">
        <span>
          RS vs NIFTY:{' '}
          <span className="font-mono font-medium text-tx-primary">
            {rs != null ? `${rs.toFixed(2)}x` : '—'}
          </span>
        </span>
        {perf21 != null && (
          <span>
            21d:{' '}
            <span className={`font-mono font-medium ${perf21 >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
              {perf21 >= 0 ? `+${perf21.toFixed(1)}%` : `${perf21.toFixed(1)}%`}
            </span>
          </span>
        )}
      </div>

      <div className="w-full bg-surface-secondary h-1.5 rounded-full overflow-hidden">
        <div 
          className={`${barColor} h-full rounded-full transition-all duration-500`} 
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </div>
  );
};

const SectorList = ({ sectors, loading = false, error = null, onRetry }) => {
  return (
    <div className="bg-surface rounded-2xl border border-border-primary shadow-sm p-6 transition-colors h-full flex flex-col justify-between">
      <div>
        <div className="flex justify-between items-start mb-1">
          <h2 className="text-lg font-heading font-bold">Leading Sectors</h2>
          <Link 
            to="/sectors" 
            className="text-accent-green text-sm font-medium hover:text-accent-green/80 flex items-center shrink-0 ml-4 transition-colors"
          >
            View all <ChevronRight className="w-4 h-4 ml-0.5" />
          </Link>
        </div>
        <p className="text-sm text-tx-secondary mb-4">
          Relative strength ratio compared to NIFTY 50 baseline (1.00x).
        </p>

        {loading ? (
          <LoadingState compact message="Fetching sector performance..." />
        ) : error ? (
          <ErrorState compact title="Sector data unavailable" message={error} onRetry={onRetry} />
        ) : !sectors || sectors.length === 0 ? (
          <EmptyState compact message="No sector performance data available." />
        ) : (
          <div className="space-y-4">
            {sectors.slice(0, 5).map((sector, idx) => (
              <SectorRow key={sector.sector || idx} sector={sector} />
            ))}
          </div>
        )}
      </div>

      <div className="pt-4 mt-4 border-t border-border-primary text-xs text-tx-secondary flex justify-between items-center">
        <span>Higher RS indicates leadership</span>
        <Link to="/sectors" className="text-accent-green hover:underline">
          Full Sector Matrix →
        </Link>
      </div>
    </div>
  );
};

export default SectorList;

