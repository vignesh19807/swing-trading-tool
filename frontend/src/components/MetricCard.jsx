import React from 'react';

const MetricCard = ({ title, value, change, isPositive, extra }) => {
  return (
    <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm flex flex-col justify-between transition-colors">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-sm font-semibold text-tx-secondary mb-1 tracking-wide">{title}</h3>
          <div className="text-3xl font-heading font-bold mb-2">{value}</div>
          {change && (
            <div className="text-sm">
              <span className={`font-medium ${isPositive ? 'text-accent-green' : 'text-accent-red'}`}>
                {change}
              </span>
              <span className="text-tx-secondary ml-1">today</span>
            </div>
          )}
        </div>
        {extra}
      </div>
    </div>
  );
};

export default MetricCard;
