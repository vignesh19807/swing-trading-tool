import React from 'react';
import { RefreshCw, AlertCircle, Inbox } from 'lucide-react';

export const LoadingState = ({ message, compact = false, className = '' }) => (
  <div 
    role="status"
    aria-live="polite"
    className={`flex flex-col items-center justify-center w-full text-center ${compact ? 'p-6' : 'p-12'} ${className}`}
  >
    <div 
      className={`animate-spin rounded-full border-2 border-accent-green/20 border-t-accent-green mb-3 ${compact ? 'h-6 w-6' : 'h-8 w-8'}`}
      aria-hidden="true"
    />
    <span className="text-xs text-tx-secondary font-medium">
      {message || 'Loading data...'}
    </span>
  </div>
);

export const ErrorState = ({ title = 'Failed to load data', message, onRetry, compact = false, className = '' }) => (
  <div 
    role="alert"
    className={`flex flex-col items-center justify-center w-full text-center border border-accent-red/25 rounded-2xl bg-accent-red/5 text-tx-primary ${compact ? 'p-4' : 'p-8'} ${className}`}
  >
    <div className="w-9 h-9 rounded-full bg-accent-red/10 text-accent-red flex items-center justify-center mb-2" aria-hidden="true">
      <AlertCircle className="w-5 h-5" />
    </div>
    <div className="text-accent-red font-semibold text-sm mb-1">{title}</div>
    <div className="text-tx-secondary text-xs mb-4 max-w-md leading-relaxed">{message || 'An unexpected error occurred'}</div>
    {onRetry && (
      <button 
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-surface border border-border-primary rounded-xl hover:bg-surface-secondary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green active:bg-surface-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-semibold text-tx-primary transition-colors cursor-pointer shadow-2xs"
      >
        <RefreshCw className="w-3.5 h-3.5 text-accent-green" />
        <span>Try Again</span>
      </button>
    )}
  </div>
);

export const EmptyState = ({ message = 'No data available', compact = false, className = '' }) => (
  <div 
    className={`flex flex-col items-center justify-center w-full text-center border border-border-primary border-dashed rounded-2xl text-tx-secondary text-sm ${compact ? 'p-6' : 'p-12'} ${className}`}
  >
    <div className="w-9 h-9 rounded-full bg-surface-secondary text-tx-muted flex items-center justify-center mb-2" aria-hidden="true">
      <Inbox className="w-5 h-5" />
    </div>
    <span className="text-xs text-tx-secondary max-w-md">{message}</span>
  </div>
);
