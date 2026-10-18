/**
 * @file WatchlistContext.jsx
 * @description React Context and Provider for synchronized cross-application watchlist state.
 *
 * FEATURES:
 *   - Automatic localStorage persistence
 *   - Cross-tab / cross-window synchronization via window storage events
 *   - Duplicate prevention with friendly visual feedback
 *   - Toast notifications on add/remove/duplicate events
 *   - O(1) watchlist lookup via Set
 */

import React, { createContext, useState, useEffect, useCallback, useMemo } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import {
  loadWatchlist,
  saveWatchlist,
  addStockToWatchlist,
  removeStockFromWatchlist,
  WATCHLIST_STORAGE_KEY,
} from '../utils/watchlistStorage';

const WatchlistContext = createContext(null);

export function WatchlistProvider({ children }) {
  const [watchlist, setWatchlist] = useState(() => {
    return loadWatchlist();
  });

  const [toast, setToast] = useState(null);

  // Auto-clear toast after 3 seconds
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => {
      setToast(null);
    }, 3200);
    return () => clearTimeout(timer);
  }, [toast]);

  // Persist to localStorage on change
  useEffect(() => {
    saveWatchlist(watchlist);
  }, [watchlist]);

  // Cross-tab synchronization
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === WATCHLIST_STORAGE_KEY) {
        setWatchlist(loadWatchlist());
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const watchlistSymbols = useMemo(() => {
    return new Set(watchlist.map((item) => (item.symbol || '').toUpperCase()));
  }, [watchlist]);

  const isInWatchlist = useCallback(
    (symbol) => {
      if (!symbol) return false;
      const clean = String(symbol).trim().toUpperCase();
      return watchlistSymbols.has(clean);
    },
    [watchlistSymbols]
  );

  const addToWatchlist = useCallback(
    (stockOrSymbol) => {
      const res = addStockToWatchlist(watchlist, stockOrSymbol);
      if (res.success) {
        setWatchlist(res.list);
        setToast({
          id: Date.now(),
          type: 'success',
          message: `Added ${res.item.symbol} to your watchlist.`,
        });
      } else if (res.isDuplicate) {
        setToast({
          id: Date.now(),
          type: 'info',
          message: `${res.item?.symbol || 'Stock'} is already in your watchlist.`,
        });
      } else {
        setToast({
          id: Date.now(),
          type: 'error',
          message: res.error || 'Failed to add stock to watchlist.',
        });
      }
      return res;
    },
    [watchlist]
  );

  const removeFromWatchlist = useCallback(
    (symbol) => {
      if (!symbol) return { success: false };
      const clean = String(symbol).trim().toUpperCase();
      const res = removeStockFromWatchlist(watchlist, clean);
      if (res.success) {
        setWatchlist(res.list);
        setToast({
          id: Date.now(),
          type: 'info',
          message: `Removed ${clean} from your watchlist.`,
        });
      }
      return res;
    },
    [watchlist]
  );

  const toggleWatchlist = useCallback(
    (stockOrSymbol) => {
      const sym = typeof stockOrSymbol === 'string'
        ? stockOrSymbol
        : stockOrSymbol?.symbol || stockOrSymbol?.ticker;

      if (!sym) return;

      if (isInWatchlist(sym)) {
        return removeFromWatchlist(sym);
      } else {
        return addToWatchlist(stockOrSymbol);
      }
    },
    [isInWatchlist, addToWatchlist, removeFromWatchlist]
  );

  const clearWatchlist = useCallback(() => {
    setWatchlist([]);
    setToast({
      id: Date.now(),
      type: 'info',
      message: 'Watchlist cleared.',
    });
  }, []);

  const value = useMemo(
    () => ({
      watchlist,
      watchlistSymbols,
      isInWatchlist,
      addToWatchlist,
      removeFromWatchlist,
      toggleWatchlist,
      clearWatchlist,
      toast,
      setToast,
    }),
    [
      watchlist,
      watchlistSymbols,
      isInWatchlist,
      addToWatchlist,
      removeFromWatchlist,
      toggleWatchlist,
      clearWatchlist,
      toast,
    ]
  );

  return (
    <WatchlistContext.Provider value={value}>
      {children}
      {/* Toast Feedback Notification Banner */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-md transition-all duration-300 animate-slide-up bg-surface border-border-primary text-tx-primary"
        >
          {toast.type === 'success' && <CheckCircle2 className="w-4 h-4 text-accent-green shrink-0" />}
          {toast.type === 'info' && <Info className="w-4 h-4 text-accent-teal shrink-0" />}
          {toast.type === 'error' && <AlertCircle className="w-4 h-4 text-accent-red shrink-0" />}

          <span className="text-xs font-medium text-tx-primary">{toast.message}</span>

          <button
            type="button"
            onClick={() => setToast(null)}
            className="p-1 text-tx-muted hover:text-tx-primary rounded transition-colors ml-1 cursor-pointer"
            aria-label="Dismiss notification"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </WatchlistContext.Provider>
  );
}

export default WatchlistContext;
