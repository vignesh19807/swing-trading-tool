import React from 'react';

export const LoadingState = () => (
  <div className="flex items-center justify-center p-12 w-full">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-green"></div>
  </div>
);

export const ErrorState = ({ message, onRetry }) => (
  <div className="flex flex-col items-center justify-center p-12 w-full text-center border border-accent-red/20 rounded-xl bg-accent-red/5">
    <div className="text-accent-red font-semibold mb-2">Failed to load data</div>
    <div className="text-tx-secondary text-sm mb-4">{message || 'An unexpected error occurred'}</div>
    {onRetry && (
      <button 
        onClick={onRetry}
        className="px-4 py-2 bg-surface border border-border-primary rounded-lg hover:bg-surface-secondary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green active:bg-surface-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
      >
        Retry
      </button>
    )}
  </div>
);

export const EmptyState = ({ message }) => (
  <div className="flex items-center justify-center p-12 w-full text-center border border-border-primary border-dashed rounded-xl text-tx-secondary">
    {message || 'No data available'}
  </div>
);
