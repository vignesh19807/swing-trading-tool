import React from 'react';

const MetricCard = ({
  title,
  value,
  change,
  changeAbsolute,
  isPositive,
  subtitle = 'today',
  extra,
  loading = false,
  error = null,
  onRetry
}) => {
  if (loading) {
    return (
      <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm flex flex-col justify-between transition-colors min-h-[140px] animate-pulse">
        <div className="flex justify-between items-start">
          <div className="w-full">
            <div className="h-4 bg-surface-secondary rounded w-24 mb-3"></div>
            <div className="h-8 bg-surface-secondary rounded w-36 mb-2"></div>
            <div className="h-4 bg-surface-secondary rounded w-20"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm flex flex-col justify-between transition-colors min-h-[140px]">
        <div>
          <h3 className="text-sm font-semibold text-tx-secondary mb-1 tracking-wide">{title}</h3>
          <div className="text-xs text-accent-red mt-2 mb-3">{error}</div>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="self-start text-xs font-medium text-accent-green hover:underline focus:outline-none"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  const changeColorClass =
    isPositive === true ? 'text-accent-green' :
    isPositive === false ? 'text-accent-red' :
    'text-tx-secondary';

  return (
    <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm flex flex-col justify-between transition-colors min-h-[140px]">
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-tx-secondary mb-1 tracking-wide uppercase truncate">{title}</h3>
          <div className="text-2xl sm:text-3xl font-heading font-bold mb-2 truncate text-tx-primary">{value}</div>
          {(change || changeAbsolute) && (
            <div className="text-sm flex items-center flex-wrap gap-1">
              {changeAbsolute && (
                <span className={`font-medium ${changeColorClass}`}>
                  {changeAbsolute}
                </span>
              )}
              {change && (
                <span className={`font-medium ${changeColorClass}`}>
                  {changeAbsolute ? `(${change})` : change}
                </span>
              )}
              {subtitle && (
                <span className="text-tx-secondary text-xs ml-0.5">{subtitle}</span>
              )}
            </div>
          )}
        </div>
        {extra && <div className="shrink-0">{extra}</div>}
      </div>
    </div>
  );
};

export default MetricCard;
