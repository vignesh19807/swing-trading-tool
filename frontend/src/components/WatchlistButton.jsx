/**
 * @file WatchlistButton.jsx
 * @description Standardized, accessible toggle button for adding/removing stocks from the watchlist.
 *
 * VARIANTS:
 *   - 'icon': Compact Star icon button for tables, header chips, and card corners.
 *   - 'button': Full pill button with Star icon and action text for stock detail pages and banners.
 *   - 'remove': Red-hover cross or trash icon for quick removal from Watchlist table/cards.
 *
 * SPECIFICATION:
 *   - Reused across Stock Explorer (/stocks), Stock Detail (/stocks/:symbol), and Watchlist (/watchlist).
 *   - Prevents click propagation to parent table row or card links.
 *   - Gold/amber filled star when active; muted outline when inactive.
 *   - Tooltip and aria-label updates dynamically.
 */

import React, { memo } from 'react';
import { Star, Trash2 } from 'lucide-react';
import { useWatchlist } from '../hooks/useWatchlist';

const WatchlistButton = ({
  stock,
  variant = 'icon',
  size = 'md',
  className = '',
  onToggled = null,
}) => {
  const { isInWatchlist, toggleWatchlist, removeFromWatchlist } = useWatchlist();

  if (!stock) return null;

  const symbol = typeof stock === 'string'
    ? stock.trim().toUpperCase()
    : (stock.symbol || stock.ticker || '').trim().toUpperCase();

  if (!symbol) return null;

  const active = isInWatchlist(symbol);

  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (variant === 'remove') {
      const res = removeFromWatchlist(symbol);
      if (onToggled) onToggled(false, stock, res);
      return;
    }

    const res = toggleWatchlist(stock);
    const nowActive = !active;
    if (onToggled) onToggled(nowActive, stock, res);
  };

  // 1. Remove-only variant (trash icon)
  if (variant === 'remove') {
    return (
      <button
        type="button"
        onClick={handleClick}
        aria-label={`Remove ${symbol} from watchlist`}
        title={`Remove ${symbol} from watchlist`}
        className={`p-1.5 rounded-lg text-tx-muted hover:text-accent-red hover:bg-accent-red/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-red transition-colors cursor-pointer ${className}`}
      >
        <Trash2 className="w-4 h-4" />
      </button>
    );
  }

  // Size mappings
  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  const currentIconSize = iconSizes[size] || iconSizes.md;

  // 2. Full Pill Button variant (Stock Detail page, action bars)
  if (variant === 'button') {
    return (
      <button
        type="button"
        onClick={handleClick}
        aria-label={active ? `Remove ${symbol} from watchlist` : `Add ${symbol} to watchlist`}
        title={active ? `In Watchlist — click to remove` : `Add ${symbol} to Watchlist`}
        className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl border text-xs sm:text-sm font-semibold transition-all shadow-xs cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 ${
          active
            ? 'bg-amber-400/10 border-amber-400/40 text-amber-500 dark:text-amber-400 hover:bg-amber-400/20'
            : 'bg-surface border-border-primary text-tx-secondary hover:text-tx-primary hover:bg-surface-secondary'
        } ${className}`}
      >
        <Star
          className={`${currentIconSize} transition-transform active:scale-125 ${
            active
              ? 'fill-amber-400 text-amber-500 dark:text-amber-400'
              : 'text-tx-muted stroke-[2]'
          }`}
        />
        <span>{active ? 'Saved in Watchlist' : 'Add to Watchlist'}</span>
      </button>
    );
  }

  // 3. Compact Icon button variant (Tables, cards)
  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={active ? `Remove ${symbol} from watchlist` : `Add ${symbol} to watchlist`}
      title={active ? `In Watchlist — click to remove ${symbol}` : `Add ${symbol} to Watchlist`}
      className={`p-1.5 rounded-lg transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 ${
        active
          ? 'text-amber-500 dark:text-amber-400 hover:bg-amber-400/10'
          : 'text-tx-muted hover:text-tx-primary hover:bg-surface-secondary'
      } ${className}`}
    >
      <Star
        className={`${currentIconSize} transition-all duration-200 active:scale-125 ${
          active
            ? 'fill-amber-400 text-amber-500 dark:text-amber-400 drop-shadow-[0_0_6px_rgba(251,191,36,0.35)]'
            : 'stroke-[2]'
        }`}
      />
    </button>
  );
};

export default memo(WatchlistButton);
