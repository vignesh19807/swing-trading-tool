import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import PlaceholderPage from './pages/PlaceholderPage';
import StockDetail from './pages/StockDetail';
import NotFound from './pages/NotFound';
import { useTheme } from './hooks/useTheme';

function App() {
  const { theme, toggleTheme } = useTheme();

  return (
    <Router>
      <MainLayout theme={theme} toggleTheme={toggleTheme}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/opportunities" element={<PlaceholderPage title="Opportunities" />} />
          <Route path="/stocks" element={<PlaceholderPage title="Stocks" />} />
          <Route path="/stocks/:symbol" element={<StockDetail />} />
          <Route path="/sectors" element={<PlaceholderPage title="Sectors" />} />
          <Route path="/watchlist" element={<PlaceholderPage title="Watchlist" />} />
          <Route path="/performance" element={<PlaceholderPage title="Performance" />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </MainLayout>
    </Router>
  );
}

export default App;
