import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import PlaceholderPage from './pages/PlaceholderPage';
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
          <Route path="/stocks/:symbol" element={<PlaceholderPage title="Stock Detail" />} />
          <Route path="/sectors" element={<PlaceholderPage title="Sectors" />} />
          <Route path="/watchlist" element={<PlaceholderPage title="Watchlist" />} />
          <Route path="/performance" element={<PlaceholderPage title="Performance" />} />
        </Routes>
      </MainLayout>
    </Router>
  );
}

export default App;
