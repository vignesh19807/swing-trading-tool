import React from 'react';
import { ChevronRight, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LoadingState, ErrorState, EmptyState } from './StateComponents';

const ScoreBadge = ({ score, max = 100 }) => {
  if (score == null || isNaN(score)) {
    return <span className="text-xs text-tx-secondary">—</span>;
  }
  const numericScore = Number(score);
  const percentage = Math.min(Math.max((numericScore / max) * 100, 0), 100);
  let color = 'bg-accent-green';
  if (percentage < 50) color = 'bg-accent-red';
  else if (percentage < 70) color = 'bg-accent-warning';

  return (
    <div className="flex items-center gap-2">
      <div className="w-12 h-2 bg-surface-secondary rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${percentage}%` }}></div>
      </div>
      <span className="text-xs font-semibold text-tx-primary">{numericScore.toFixed(1)}</span>
    </div>
  );
};

const OpportunityRow = ({ opp }) => {
  const formattedPrice = opp.current_price != null && !isNaN(opp.current_price)
    ? `₹${Number(opp.current_price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '—';

  const formattedRR = opp.risk_reward != null && !isNaN(opp.risk_reward)
    ? `${Number(opp.risk_reward).toFixed(1)}x`
    : '—';

  return (
    <div className="flex flex-col md:table-row md:hover:bg-surface-secondary/60 p-4 md:p-0 border-b border-border-primary last:border-0 transition-colors">
      {/* Symbol & Company */}
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 font-bold text-tx-primary flex justify-between items-center md:table-cell">
        <span className="md:hidden text-tx-muted text-xs font-normal">STOCK</span>
        <div>
          <Link 
            to={`/stocks/${encodeURIComponent(opp.symbol)}`}
            className="text-tx-primary hover:text-accent-green inline-flex items-center gap-1 font-heading font-semibold text-base transition-colors"
          >
            {opp.symbol}
            <ArrowUpRight className="w-3.5 h-3.5 opacity-60" />
          </Link>
          {opp.company_name && (
            <div className="text-xs text-tx-secondary font-normal truncate max-w-[180px]">
              {opp.company_name}
            </div>
          )}
        </div>
      </div>

      {/* Composite Opportunity Score */}
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">SCORE</span>
        <ScoreBadge score={opp.opportunity_score} />
      </div>

      {/* Current Price */}
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 font-medium flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">PRICE</span>
        <span className="text-tx-primary font-mono text-sm">{formattedPrice}</span>
      </div>

      {/* Technical Score Setup */}
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">SETUP</span>
        <ScoreBadge score={opp.technical_score} />
      </div>

      {/* Risk / Recommendation */}
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">SIGNAL</span>
        <div className="flex items-center gap-1.5">
          {opp.recommendation ? (
            <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
              opp.recommendation === 'BUY' 
                ? 'bg-accent-green/10 text-accent-green border border-accent-green/20' 
                : 'bg-surface-secondary text-tx-secondary border border-border-primary'
            }`}>
              {opp.recommendation}
            </span>
          ) : (
            <span className="text-xs text-tx-secondary">—</span>
          )}
          {opp.risk_score != null && (
            <span className="text-xs text-tx-secondary px-1.5 py-0.5 bg-surface-secondary rounded">
              Risk: {opp.risk_score}
            </span>
          )}
        </div>
      </div>

      {/* Risk-to-Reward Ratio */}
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">R/R</span>
        <span className="text-accent-green font-medium font-mono text-sm">{formattedRR}</span>
      </div>
    </div>
  );
};

const OpportunityTable = ({ opportunities, loading = false, error = null, onRetry }) => {
  return (
    <div className="bg-surface rounded-2xl border border-border-primary shadow-sm transition-colors h-full flex flex-col justify-between">
      <div>
        <div className="p-6 border-b border-border-primary flex justify-between items-start">
          <div>
            <h2 className="text-lg font-heading font-bold mb-1">Top Swing Opportunities</h2>
            <p className="text-sm text-tx-secondary">
              Highest-scoring setups from the multi-factor decision engine.
            </p>
          </div>
          <Link 
            to="/opportunities" 
            className="text-accent-green text-sm font-medium hover:text-accent-green/80 flex items-center shrink-0 ml-4 transition-colors"
          >
            View all <ChevronRight className="w-4 h-4 ml-0.5" />
          </Link>
        </div>

        {loading ? (
          <LoadingState compact message="Fetching swing opportunities..." />
        ) : error ? (
          <div className="p-6">
            <ErrorState compact title="Could not load opportunities" message={error} onRetry={onRetry} />
          </div>
        ) : !opportunities || opportunities.length === 0 ? (
          <div className="p-6">
            <EmptyState compact message="No qualifying swing opportunities found in the current universe scan." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div className="w-full md:table text-sm">
              <div className="hidden md:table-header-group">
                <div className="table-row text-tx-secondary font-semibold text-xs tracking-wider text-left bg-surface-secondary/50">
                  <div className="table-cell px-6 py-3.5">STOCK</div>
                  <div className="table-cell px-6 py-3.5">OPPORTUNITY SCORE</div>
                  <div className="table-cell px-6 py-3.5">PRICE</div>
                  <div className="table-cell px-6 py-3.5">TECH SETUP</div>
                  <div className="table-cell px-6 py-3.5">SIGNAL / RISK</div>
                  <div className="table-cell px-6 py-3.5">R/R RATIO</div>
                </div>
              </div>
              <div className="md:table-row-group divide-y divide-border-primary">
                {opportunities.map((opp, idx) => (
                  <OpportunityRow key={opp.symbol || idx} opp={opp} />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-border-primary bg-surface-secondary/30 flex justify-between items-center text-xs text-tx-secondary">
        <span>Scored on Technical, Financial, Sector & Risk metrics</span>
        <Link to="/opportunities" className="text-accent-green hover:underline">
          Open Screener →
        </Link>
      </div>
    </div>
  );
};

export default OpportunityTable;

