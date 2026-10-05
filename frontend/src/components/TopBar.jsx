import React from 'react';
import { Search, Bell, Menu, User, Sun, Moon } from 'lucide-react';
import { useLocation } from 'react-router-dom';

const routeNames = {
  '/': 'Dashboard',
  '/opportunities': 'Opportunities',
  '/stocks': 'Stocks',
  '/sectors': 'Sectors',
  '/watchlist': 'Watchlist',
  '/performance': 'Performance'
};

const TopBar = ({ onMenuClick, theme, toggleTheme }) => {
  const location = useLocation();

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
        <button className="md:hidden p-2 -ml-2 rounded-lg text-tx-secondary hover:text-tx-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green transition-colors" onClick={onMenuClick}>
          <Menu className="w-6 h-6" />
        </button>
        <h2 className="font-heading font-semibold text-lg hidden md:block">{pageTitle}</h2>
        <div className="relative w-full max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-tx-muted" />
          <input
            type="text"
            placeholder="Search stocks, symbols..."
            className="w-full bg-surface-secondary text-tx-primary rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-green/20 border border-transparent focus:border-accent-green/30 transition-colors"
          />
        </div>
      </div>
      <div className="flex items-center gap-3 md:gap-4 text-tx-secondary">
        <button 
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="hover:text-tx-primary transition-colors p-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green rounded-full"
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
        <button className="hover:text-tx-primary transition-colors p-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green rounded-full">
          <Bell className="w-5 h-5" />
        </button>
        <button className="w-8 h-8 rounded-full bg-accent-green/10 text-accent-green flex items-center justify-center hover:bg-accent-green/20 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green">
          <User className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};

export default TopBar;
