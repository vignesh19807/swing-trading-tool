import React, { useState, useEffect, useRef } from 'react';
import { Search, Bell, Menu, User, Sun, Moon, ArrowUpRight, X } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getStocks } from '../services/api';

const routeNames = {
  '/': 'Dashboard',
  '/opportunities': 'Opportunities',
  '/stocks': 'Stocks',
  '/sectors': 'Sectors',
  '/watchlist': 'Watchlist',
  '/performance': 'Performance',
  '/settings': 'Settings',
  '/data-health': 'Data Health',
};

const TopBar = ({ onMenuClick, theme, toggleTheme }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [stocks, setStocks] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const containerRef = useRef(null);

  useEffect(() => {
    let active = true;
    getStocks()
      .then(res => {
        if (!active) return;
        const list = Array.isArray(res) ? res : res?.stocks || [];
        setStocks(list);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // Filter stocks based on query (symbol, company_name, sector)
  const suggestions = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return stocks
      .filter(s => {
        const sym = (s.symbol || '').toLowerCase();
        const name = (s.company_name || '').toLowerCase();
        const sec = (s.sector || '').toLowerCase();
        return sym.includes(q) || name.includes(q) || sec.includes(q);
      })
      .slice(0, 6);
  }, [stocks, query]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  // Reset dropdown on route change
  useEffect(() => {
    setIsOpen(false);
    setSelectedIndex(-1);
  }, [location.pathname]);

  const handleSelectStock = (stock) => {
    setQuery('');
    setIsOpen(false);
    navigate(`/stocks/${encodeURIComponent(stock.symbol)}`);
  };

  const handleKeyDown = (e) => {
    if (!isOpen || suggestions.length === 0) {
      if (e.key === 'Enter' && query.trim()) {
        const exactMatch = stocks.find(
          s => s.symbol.toLowerCase() === query.trim().toLowerCase()
        );
        if (exactMatch) {
          handleSelectStock(exactMatch);
        } else {
          navigate(`/stocks?search=${encodeURIComponent(query.trim())}`);
          setIsOpen(false);
        }
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
        handleSelectStock(suggestions[selectedIndex]);
      } else {
        const exactMatch = stocks.find(
          s => s.symbol.toLowerCase() === query.trim().toLowerCase()
        );
        if (exactMatch) {
          handleSelectStock(exactMatch);
        } else {
          navigate(`/stocks?search=${encodeURIComponent(query.trim())}`);
          setIsOpen(false);
        }
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const getPageTitle = (pathname) => {
    if (routeNames[pathname]) return routeNames[pathname];
    
    if (pathname.startsWith('/stocks/')) {
      const symbol = pathname.split('/')[2];
      return symbol ? `Stock Detail: ${decodeURIComponent(symbol).toUpperCase()}` : 'Stock Detail';
    }
    
    return 'Swing-tool';
  };

  const pageTitle = getPageTitle(location.pathname);

  return (
    <header className="h-[72px] bg-surface border-b border-border-primary flex items-center justify-between px-4 md:px-8 shrink-0 transition-colors">
      <div className="flex items-center gap-4 md:gap-8 flex-1">
        <button 
          type="button"
          aria-label="Open navigation menu"
          className="md:hidden p-2 -ml-2 rounded-lg text-tx-secondary hover:text-tx-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green transition-colors cursor-pointer" 
          onClick={onMenuClick}
        >
          <Menu className="w-6 h-6" />
        </button>
        <h2 className="font-heading font-semibold text-lg hidden md:block">{pageTitle}</h2>
        
        {/* Global Search Autocomplete Bar */}
        <div ref={containerRef} className="relative w-full max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-tx-muted" aria-hidden="true" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
              setSelectedIndex(-1);
            }}
            onFocus={() => {
              if (query.trim()) setIsOpen(true);
            }}
            onKeyDown={handleKeyDown}
            aria-label="Search stocks, symbols..."
            placeholder="Search stocks, symbols (e.g. INFY, Infosys)..."
            className="w-full bg-surface-secondary text-tx-primary rounded-lg pl-9 pr-8 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-green/20 border border-transparent focus:border-accent-green/30 transition-colors"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery('');
                setIsOpen(false);
              }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-tx-muted hover:text-tx-primary p-0.5 rounded cursor-pointer"
              title="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Autocomplete Suggestions Menu */}
          {isOpen && query.trim() && (
            <div className="absolute top-full left-0 right-0 mt-1.5 bg-surface border border-border-primary rounded-xl shadow-lg z-50 overflow-hidden py-1 max-h-72 overflow-y-auto animate-fade-in">
              {suggestions.length > 0 ? (
                <div>
                  <div className="px-3 py-1.5 text-[11px] font-semibold text-tx-muted uppercase tracking-wider">
                    Matching Equities
                  </div>
                  {suggestions.map((stock, idx) => (
                    <button
                      key={stock.symbol}
                      type="button"
                      onClick={() => handleSelectStock(stock)}
                      className={`w-full text-left px-3.5 py-2 flex items-center justify-between text-xs transition-colors cursor-pointer ${
                        idx === selectedIndex ? 'bg-surface-secondary text-accent-green font-medium' : 'text-tx-primary hover:bg-surface-secondary/80'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-mono font-bold text-sm text-tx-primary">{stock.symbol}</span>
                        {stock.company_name && (
                          <span className="text-tx-secondary truncate max-w-[200px]">{stock.company_name}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {stock.sector && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-secondary text-tx-muted border border-border-primary/50">
                            {stock.sector}
                          </span>
                        )}
                        <ArrowUpRight className="w-3.5 h-3.5 opacity-60" />
                      </div>
                    </button>
                  ))}
                  <div className="border-t border-border-primary/50 mt-1 pt-1 px-3 py-1.5 flex justify-between items-center text-[11px] text-tx-muted bg-surface-secondary/30">
                    <span>Press <strong>Enter</strong> to view all in Screener</span>
                    <button
                      type="button"
                      onClick={() => {
                        navigate(`/stocks?search=${encodeURIComponent(query.trim())}`);
                        setIsOpen(false);
                      }}
                      className="text-accent-green hover:underline font-medium"
                    >
                      Explore All →
                    </button>
                  </div>
                </div>
              ) : (
                <div className="px-4 py-3 text-xs text-tx-secondary text-center">
                  <div>No stocks found matching "{query}"</div>
                  <button
                    type="button"
                    onClick={() => {
                      navigate(`/stocks?search=${encodeURIComponent(query.trim())}`);
                      setIsOpen(false);
                    }}
                    className="text-accent-green text-[11px] hover:underline mt-1 font-medium block mx-auto"
                  >
                    Search in Screener anyway →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3 md:gap-4 text-tx-secondary">
        <button 
          type="button"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="hover:text-tx-primary transition-colors p-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green rounded-full cursor-pointer"
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
        <button 
          type="button"
          aria-label="Notifications"
          className="hover:text-tx-primary transition-colors p-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green rounded-full cursor-pointer"
        >
          <Bell className="w-5 h-5" />
        </button>
        <button 
          type="button"
          aria-label="User profile"
          className="w-8 h-8 rounded-full bg-accent-green/10 text-accent-green flex items-center justify-center hover:bg-accent-green/20 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green cursor-pointer"
        >
          <User className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};

export default TopBar;
