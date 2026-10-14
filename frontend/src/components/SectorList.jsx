import React from 'react';
import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const SectorRow = ({ sector }) => {
  // Mock strength score logic based on relative strength
  const strengthScore = Math.min(Math.max((sector.relative_strength_vs_nifty * 100) - 20, 0), 100);
  
  let label = "Neutral";
  let color = "bg-accent-warning";
  let textColor = "text-accent-warning";
  
  if (strengthScore > 80) {
    label = "Strong";
    color = "bg-accent-green";
    textColor = "text-accent-green";
  } else if (strengthScore < 40) {
    label = "Weak";
    color = "bg-accent-red";
    textColor = "text-accent-red";
  }

  return (
    <div>
      <div className="flex justify-between items-end mb-2">
        <span className="font-semibold text-tx-primary">{sector.sector}</span>
        <div className="text-sm">
          <span className={`${textColor} font-medium`}>{label}</span>
          <span className="font-heading font-bold text-tx-primary ml-2">{Math.round(strengthScore)}</span>
        </div>
      </div>
      <div className="w-full bg-surface-secondary h-2 rounded-full overflow-hidden">
        <div className={`${color} h-full rounded-full transition-all duration-500`} style={{ width: `${strengthScore}%` }}></div>
      </div>
    </div>
  );
};

const SectorList = ({ sectors }) => {
  return (
    <div className="bg-surface rounded-xl border border-border-primary shadow-sm p-6 transition-colors h-full">
      <div className="flex justify-between items-start mb-2">
        <h2 className="text-lg font-heading font-bold">Strongest Sectors</h2>
        <Link to="/sectors" className="text-accent-green text-sm font-medium hover:text-accent-green/80 flex items-center shrink-0 ml-4 transition-colors">
          View all <ChevronRight className="w-4 h-4 ml-0.5" />
        </Link>
      </div>
      <p className="text-sm text-tx-secondary mb-6">Sector strength based on current analysis.</p>

      <div className="space-y-6">
        {sectors.slice(0, 5).map((sector, idx) => (
          <SectorRow key={idx} sector={sector} />
        ))}
      </div>
    </div>
  );
};

export default SectorList;
