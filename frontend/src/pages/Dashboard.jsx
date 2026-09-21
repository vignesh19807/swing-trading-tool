import React, { useState, useEffect } from 'react';
import { 
  getMarketIndices, 
  getOpportunities, 
  getSectors, 
  getDataHealth 
} from '../services/api';
import MetricCard from '../components/MetricCard';
import OpportunityTable from '../components/OpportunityTable';
import SectorList from '../components/SectorList';
import { LoadingState, ErrorState } from '../components/StateComponents';
import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const MiniChart = () => (
  <svg
    viewBox="0 0 100 40"
    className="w-24 h-12 text-accent-green"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M0 30L20 15L40 25L60 10L80 20L100 5"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M0 30L20 15L40 25L60 10L80 20L100 5V40H0V30Z"
      fill="currentColor"
      fillOpacity="0.1"
    />
  </svg>
);

const Dashboard = () => {
  const [data, setData] = useState({
    indices: null,
    opportunities: null,
    sectors: null,
    health: null
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [indicesRes, oppsRes, sectorsRes, healthRes] = await Promise.all([
        getMarketIndices(),
        getOpportunities(),
        getSectors(),
        getDataHealth()
      ]);

      setData({
        indices: indicesRes,
        opportunities: oppsRes,
        sectors: sectorsRes,
        health: healthRes
      });
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      setError('Could not connect to the market data service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchData} />;
  }

  const { indices, opportunities, sectors, health } = data;

  return (
    <div className="p-4 md:p-8 h-full">
      <div className="mb-8">
        <h1 className="text-2xl font-heading font-bold mb-1">Market Intelligence</h1>
        <p className="text-tx-secondary text-sm">Indian equities · Swing horizon 3-8 weeks</p>
      </div>

      {/* Top Cards Row */}
      {indices && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* NIFTY 50 Card */}
          <MetricCard 
            title="NIFTY 50"
            value={indices.nifty50.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            change={`+${indices.nifty50.change_percent}%`}
            isPositive={indices.nifty50.is_positive}
            extra={<MiniChart />}
          />

          {/* SENSEX Card */}
          <MetricCard 
            title="SENSEX"
            value={indices.sensex.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            change={`+${indices.sensex.change_percent}%`}
            isPositive={indices.sensex.is_positive}
            extra={<MiniChart />}
          />

          {/* Market Condition Card */}
          <div className="bg-surface rounded-xl p-6 border border-border-primary shadow-sm transition-colors">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-sm font-semibold text-tx-secondary tracking-wide uppercase">Market Condition</h3>
              <span className="px-2.5 py-1 bg-accent-green/10 text-accent-green text-xs font-medium rounded-full">
                {indices.condition.label}
              </span>
            </div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2.5 h-2.5 rounded-full bg-accent-green"></div>
              <div className="text-2xl font-heading font-bold">{indices.condition.status}</div>
            </div>
            <p className="text-sm text-tx-secondary mb-4">{indices.condition.description}</p>
            
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-tx-secondary">Advancing stocks</span>
                <span className="text-accent-green font-medium">{indices.condition.advancing.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-tx-secondary">Declining stocks</span>
                <span className="text-accent-red font-medium">{indices.condition.declining.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          {opportunities && <OpportunityTable opportunities={opportunities} />}
        </div>
        <div className="lg:col-span-1">
          {sectors && <SectorList sectors={sectors} />}
        </div>
      </div>
      
      {/* Why These Opportunities & Data Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-surface rounded-xl border border-border-primary shadow-sm p-6">
          <div className="flex justify-between items-start mb-4">
            <h2 className="text-lg font-heading font-bold">Why These Opportunities</h2>
            <Link to="/opportunities" className="text-accent-green text-sm font-medium hover:text-accent-green/80 flex items-center shrink-0 ml-4 transition-colors">
              Full analysis <ChevronRight className="w-4 h-4 ml-0.5" />
            </Link>
          </div>
          <p className="text-sm text-tx-secondary mb-4">
            These opportunities score highly across multiple dimensions in the backend decision engine:
          </p>
          <ul className="text-sm text-tx-primary space-y-3 list-disc list-inside">
            <li><strong>Technical:</strong> Strong momentum, clear trend alignment, and favorable moving averages.</li>
            <li><strong>Financial:</strong> Solid earnings growth and healthy margins.</li>
            <li><strong>Risk:</strong> Optimal reward-to-risk ratio (R/R) with clearly defined stop-loss levels.</li>
          </ul>
        </div>

        <div className="lg:col-span-1 bg-surface rounded-xl border border-border-primary shadow-sm p-6">
          <h2 className="text-lg font-heading font-bold mb-4">Data Health</h2>
          {health ? (
            <div className="space-y-4 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-tx-secondary">Market Data</span>
                <span className="px-2.5 py-1 bg-accent-green/10 text-accent-green text-xs font-medium rounded-full">
                  {health.market_data}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-tx-secondary">Technical Data</span>
                <span className="px-2.5 py-1 bg-accent-green/10 text-accent-green text-xs font-medium rounded-full">
                  {health.technical_data}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-tx-secondary">Financial Data</span>
                <span className="px-2.5 py-1 bg-accent-green/10 text-accent-green text-xs font-medium rounded-full">
                  {health.financial_data}
                </span>
              </div>
              <div className="pt-4 mt-4 border-t border-border-primary text-xs text-tx-muted">
                Last updated: {new Date(health.last_updated).toLocaleString()}
              </div>
            </div>
          ) : (
            <div className="text-sm text-tx-secondary">Health status unavailable.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
