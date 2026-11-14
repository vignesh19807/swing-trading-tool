import React from 'react';

export const LoadingState = ({ message, compact = false, className = '' }) => (
  <div className={`flex flex-col items-center justify-center w-full ${compact ? 'p-6' : 'p-12'} ${className}`}>
    <div className={`animate-spin rounded-full border-b-2 border-accent-green mb-2 ${compact ? 'h-6 w-6' : 'h-8 w-8'}`}></div>
    {message && <div className="text-xs text-tx-secondary">{message}</div>}
  </div>
);

export const ErrorState = ({ title = 'Failed to load data', message, onRetry, compact = false, className = '' }) => (
  <div className={`flex flex-col items-center justify-center w-full text-center border border-accent-red/20 rounded-xl bg-accent-red/5 ${compact ? 'p-4' : 'p-8'} ${className}`}>
    <div className="text-accent-red font-semibold text-sm mb-1">{title}</div>
    <div className="text-tx-secondary text-xs mb-3 max-w-md">{message || 'An unexpected error occurred'}</div>
    {onRetry && (
      <button 
        type="button"
        onClick={onRetry}
        className="px-3 py-1.5 bg-surface border border-border-primary rounded-lg hover:bg-surface-secondary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green active:bg-surface-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-medium transition-colors"
      >
        Retry
      </button>
    )}
  </div>
);

export const EmptyState = ({ message = 'No data available', compact = false, className = '' }) => (
  <div className={`flex items-center justify-center w-full text-center border border-border-primary border-dashed rounded-xl text-tx-secondary text-sm ${compact ? 'p-6' : 'p-12'} ${className}`}>
    {message}
  </div>
);

