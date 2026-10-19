import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Sparkles,
  BarChart2,
  Layers,
  Star,
  TrendingUp,
  Moon,
  Sun,
  Settings,
  Database,
  X
} from 'lucide-react';
import { useWatchlist } from '../hooks/useWatchlist';

const SidebarItem = ({ icon: Icon, label, to, onClick, isActive, badge = null }) => (
  <Link
    to={to}
    onClick={onClick}
    aria-current={isActive ? 'page' : undefined}
    className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl mb-1 cursor-pointer transition-all duration-150 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green ${
      isActive
        ? 'bg-white text-deep-navy font-semibold shadow-xs'
        : 'text-tx-muted hover:text-white hover:bg-white/10'
    }`}
  >
    <div className="flex items-center min-w-0">
      <Icon className={`w-4.5 h-4.5 mr-3 shrink-0 ${isActive ? 'text-deep-navy' : ''}`} />
      <span className="text-sm truncate">{label}</span>
    </div>
    {badge != null && badge > 0 && (
      <span className="px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-amber-400 text-deep-navy shadow-xs shrink-0 ml-2">
        {badge}
      </span>
    )}
  </Link>
);

const Sidebar = ({ isOpen, onClose, theme, toggleTheme }) => {
  const { watchlist } = useWatchlist();
  const location = useLocation();

  /**
   * Deterministically calculates active navigation item using the real React Router location.
   * Prevents false active states on root '/' or parent routes during other page views.
   */
  const isRouteActive = (to, exact = false) => {
    const currentPath = location.pathname;
    if (exact || to === '/') {
      return currentPath === to;
    }
    return currentPath === to || currentPath.startsWith(`${to}/`);
  };

  return (
    <>
      {/* Mobile backdrop overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 md:hidden animate-fade-in" 
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      
      {/* Sidebar container */}
      <aside 
        aria-label="Main navigation"
        className={`fixed md:static inset-y-0 left-0 z-50 w-64 bg-deep-navy text-white flex flex-col h-full max-h-screen shrink-0 transform transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 select-none`}
      >
        {/* Brand / Header */}
        <div className="p-5 flex justify-between items-center shrink-0 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div 
              className="w-8 h-8 rounded-lg bg-accent-green/20 text-accent-green flex items-center justify-center font-bold text-base shadow-xs" 
              aria-hidden="true"
            >
              A
            </div>
            <div>
              <div className="font-bold text-base leading-tight tracking-tight">Swing-tool</div>
              <span className="text-[10px] text-tx-muted font-semibold tracking-wider">INTELLIGENCE</span>
            </div>
          </div>
          <button 
            type="button"
            aria-label="Close navigation"
            className="md:hidden text-tx-muted hover:text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green rounded-lg p-1.5 cursor-pointer" 
            onClick={onClose}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Navigation section */}
        <nav 
          aria-label="Sidebar navigation links"
          className="px-3 py-3 flex-1 min-h-0 overflow-y-auto overflow-x-hidden sidebar-scroll"
        >
          <div className="text-[11px] font-semibold text-tx-muted mb-2 px-3 tracking-wider uppercase">
            Navigation
          </div>
          <SidebarItem 
            icon={LayoutDashboard} 
            label="Dashboard" 
            to="/" 
            onClick={onClose} 
            isActive={isRouteActive('/', true)} 
          />
          <SidebarItem 
            icon={Sparkles} 
            label="Opportunities" 
            to="/opportunities" 
            onClick={onClose} 
            isActive={isRouteActive('/opportunities', true)} 
          />
          <SidebarItem 
            icon={BarChart2} 
            label="Stocks" 
            to="/stocks" 
            onClick={onClose} 
            isActive={isRouteActive('/stocks', false)} 
          />
          <SidebarItem 
            icon={Layers} 
            label="Sectors" 
            to="/sectors" 
            onClick={onClose} 
            isActive={isRouteActive('/sectors', false)} 
          />
          <SidebarItem 
            icon={Star} 
            label="Watchlist" 
            to="/watchlist" 
            onClick={onClose} 
            isActive={isRouteActive('/watchlist', true)} 
            badge={watchlist.length} 
          />
          <SidebarItem 
            icon={TrendingUp} 
            label="Performance" 
            to="/performance" 
            onClick={onClose} 
            isActive={isRouteActive('/performance', true)} 
          />
        </nav>

        {/* Fixed / Stable Bottom Section */}
        <div className="px-3 pt-3 pb-4 border-t border-white/5 shrink-0 mt-auto bg-deep-navy">
          {/* Market / Data Healthy panel */}
          <div className="bg-secondary-navy/80 border border-white/5 rounded-xl p-3 mb-2.5">
            <div className="flex justify-between items-center text-[11px] text-tx-muted mb-1.5 font-medium">
              <span>Market</span>
              <span>NSE / BSE</span>
            </div>
            <div className="flex items-center text-xs font-semibold text-white">
              <span className="w-2 h-2 rounded-full bg-accent-green mr-2 shrink-0 animate-pulse" aria-hidden="true" />
              Data Healthy
            </div>
          </div>
          
          {/* Settings & Theme Utilities */}
          <div className="space-y-0.5">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
              className="w-full flex items-center px-3.5 py-2.5 rounded-xl mb-1 cursor-pointer transition-all duration-150 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green text-tx-muted hover:text-white hover:bg-white/10"
            >
              {theme === 'light' ? (
                <Moon className="w-4.5 h-4.5 mr-3 shrink-0" />
              ) : (
                <Sun className="w-4.5 h-4.5 mr-3 shrink-0" />
              )}
              <span className="text-sm">{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
            </button>
            <SidebarItem 
              icon={Settings} 
              label="Settings" 
              to="/settings" 
              onClick={onClose} 
              isActive={isRouteActive('/settings', true)} 
            />
            <SidebarItem 
              icon={Database} 
              label="Data Health" 
              to="/data-health" 
              onClick={onClose} 
              isActive={isRouteActive('/data-health', true)} 
            />
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
