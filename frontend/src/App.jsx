import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Opportunities from './pages/Opportunities';
import StockExplorer from './pages/StockExplorer';
import SectorExplorer from './pages/SectorExplorer';
import PlaceholderPage from './pages/PlaceholderPage';
import StockDetail from './pages/StockDetail';
import Watchlist from './pages/Watchlist';
import Performance from './pages/Performance';
import NotFound from './pages/NotFound';
import { useTheme } from './hooks/useTheme';
import { WatchlistProvider } from './context/WatchlistContext';

function App() {
  const { theme, toggleTheme } = useTheme();

  return (
    <WatchlistProvider>
      <Router>
        <MainLayout theme={theme} toggleTheme={toggleTheme}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/opportunities" element={<Opportunities />} />
            <Route path="/stocks" element={<StockExplorer />} />
            <Route path="/stocks/:symbol" element={<StockDetail />} />
            <Route path="/sectors" element={<SectorExplorer />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
            <Route path="/data-health" element={<PlaceholderPage title="Data Health" />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </MainLayout>
      </Router>
    </WatchlistProvider>
  );
}

export default App;
