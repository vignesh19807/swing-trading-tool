import React from 'react';
import { NavLink } from 'react-router-dom';
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

const SidebarItem = ({ icon: Icon, label, to, onClick, end = false, badge = null }) => (
  <NavLink
    to={to}
    end={end}
    onClick={onClick}
    className={({ isActive }) =>
      `flex items-center justify-between px-4 py-3 rounded-lg mb-1 cursor-pointer transition-all duration-150 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green ${
        isActive
          ? 'bg-white text-deep-navy font-semibold'
          : 'text-tx-muted hover:text-white hover:bg-white/10'
      }`
    }
  >
    <div className="flex items-center">
      <Icon className="w-5 h-5 mr-3" />
      <span className="text-sm">{label}</span>
    </div>
    {badge != null && badge > 0 && (
      <span className="px-2 py-0.2 rounded-full text-[11px] font-mono font-bold bg-amber-400 text-deep-navy shadow-xs">
        {badge}
      </span>
    )}
  </NavLink>
);

const Sidebar = ({ isOpen, onClose, theme, toggleTheme }) => {
  const { watchlist } = useWatchlist();

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden" 
          onClick={onClose}
        />
      )}
      
      {/* Sidebar container */}
      <aside 
        className={`fixed md:static inset-y-0 left-0 z-50 w-64 bg-deep-navy text-white flex flex-col h-full transform transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0`}
      >
        <div className="p-6 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-accent-green/20 text-accent-green flex items-center justify-center font-bold text-lg">
              A
            </div>
            <div>
              <h1 className="font-bold text-base leading-tight">Swing-tool</h1>
              <span className="text-[10px] text-tx-muted font-semibold tracking-wider">INTELLIGENCE</span>
            </div>
          </div>
          <button 
            className="md:hidden text-tx-muted hover:text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green rounded" 
            onClick={onClose}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-4 flex-1 overflow-y-auto">
          <div className="text-xs font-semibold text-tx-muted mb-3 px-4 tracking-wider mt-2">
            NAVIGATION
          </div>
          <SidebarItem icon={LayoutDashboard} label="Dashboard" to="/" end onClick={onClose} />
          <SidebarItem icon={Sparkles} label="Opportunities" to="/opportunities" end onClick={onClose} />
          <SidebarItem icon={BarChart2} label="Stocks" to="/stocks" onClick={onClose} />
          <SidebarItem icon={Layers} label="Sectors" to="/sectors" onClick={onClose} />
          <SidebarItem icon={Star} label="Watchlist" to="/watchlist" onClick={onClose} badge={watchlist.length} />
          <SidebarItem icon={TrendingUp} label="Performance" to="/performance" onClick={onClose} />
        </div>

        <div className="px-4 pb-6 space-y-4">
          <div className="bg-secondary-navy rounded-lg p-4 mb-4">
            <div className="flex justify-between items-center text-xs text-tx-muted mb-2">
              <span>Market</span>
              <span>NSE / BSE</span>
            </div>
            <div className="flex items-center text-sm font-medium">
              <div className="w-2 h-2 rounded-full bg-accent-green mr-2"></div>
              Data Healthy
            </div>
          </div>
          
          <div className="space-y-1">
            <button
              onClick={toggleTheme}
              className="w-full flex items-center px-4 py-3 rounded-lg mb-1 cursor-pointer transition-all duration-150 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green text-tx-muted hover:text-white hover:bg-white/10"
            >
              {theme === 'light' ? <Moon className="w-5 h-5 mr-3" /> : <Sun className="w-5 h-5 mr-3" />}
              <span className="text-sm">{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
            </button>
            <SidebarItem icon={Settings} label="Settings" to="/settings" onClick={onClose} />
            <SidebarItem icon={Database} label="Data Health" to="/data-health" onClick={onClose} />
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
