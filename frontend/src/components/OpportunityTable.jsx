import React from 'react';
import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const ScoreBadge = ({ score, max = 100 }) => {
  const percentage = (score / max) * 100;
  let color = 'bg-accent-green';
  if (percentage < 40) color = 'bg-accent-red';
  else if (percentage < 70) color = 'bg-accent-warning';

  return (
    <div className="flex items-center gap-2">
      <div className="w-12 h-1.5 bg-surface-secondary rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${percentage}%` }}></div>
      </div>
      <span className="text-xs font-semibold">{score.toFixed(1)}</span>
    </div>
  );
};

const OpportunityRow = ({ opp }) => {
  return (
    <div className="flex flex-col md:table-row md:hover:bg-surface-secondary p-4 md:p-0 border-b border-border-primary last:border-0 transition-colors">
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 font-bold text-tx-primary flex justify-between md:table-cell">
        <span className="md:hidden text-tx-muted text-xs font-normal">STOCK</span>
        <span>{opp.symbol}</span>
      </div>
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">SCORE</span>
        <ScoreBadge score={opp.opportunity_score} />
      </div>
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 font-medium flex justify-between">
        <span className="md:hidden text-tx-muted text-xs font-normal">PRICE</span>
        <span>₹{opp.current_price.toLocaleString()}</span>
      </div>
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">SETUP</span>
        <ScoreBadge score={opp.technical_score} />
      </div>
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">RISK</span>
        <span className="px-2 py-1 bg-surface-secondary text-tx-primary text-xs font-medium rounded">
          {opp.risk_score}
        </span>
      </div>
      <div className="md:table-cell px-2 md:px-6 py-2 md:py-4 flex justify-between items-center">
        <span className="md:hidden text-tx-muted text-xs font-normal">R/R</span>
        <span className="text-accent-green font-medium">{opp.risk_reward}x</span>
      </div>
    </div>
  );
};

const OpportunityTable = ({ opportunities }) => {
  return (
    <div className="bg-surface rounded-xl border border-border-primary shadow-sm transition-colors">
      <div className="p-6 border-b border-border-primary flex justify-between items-start">
        <div>
          <h2 className="text-lg font-heading font-bold mb-1">Top Swing Opportunities</h2>
          <p className="text-sm text-tx-secondary">Highest-scoring opportunities based on current technical, financial, sector and risk analysis.</p>
        </div>
        <Link to="/opportunities" className="text-accent-green text-sm font-medium hover:text-accent-green/80 flex items-center shrink-0 ml-4 transition-colors">
          View all <ChevronRight className="w-4 h-4 ml-0.5" />
        </Link>
      </div>
      <div className="overflow-hidden">
        <div className="w-full md:table text-sm">
          <div className="hidden md:table-header-group">
            <div className="table-row text-tx-secondary font-semibold text-xs tracking-wider text-left bg-surface-secondary/50">
              <div className="table-cell px-6 py-4">STOCK</div>
              <div className="table-cell px-6 py-4">SCORE</div>
              <div className="table-cell px-6 py-4">PRICE</div>
              <div className="table-cell px-6 py-4">SETUP</div>
              <div className="table-cell px-6 py-4">RISK</div>
              <div className="table-cell px-6 py-4">R/R</div>
            </div>
          </div>
          <div className="md:table-row-group divide-y divide-border-primary">
            {opportunities.map((opp, idx) => (
              <OpportunityRow key={idx} opp={opp} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OpportunityTable;
