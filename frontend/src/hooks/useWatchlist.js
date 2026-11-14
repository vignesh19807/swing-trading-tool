/**
 * @file useWatchlist.js
 * @description Hook exposing watchlist state and actions from WatchlistContext.
 */

import { useContext } from 'react';
import WatchlistContext from '../context/WatchlistContext';

export function useWatchlist() {
  const context = useContext(WatchlistContext);
  if (!context) {
    throw new Error('useWatchlist must be used within a <WatchlistProvider>');
  }
  return context;
}
