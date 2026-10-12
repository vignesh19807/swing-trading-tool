import React from 'react';
import { useParams } from 'react-router-dom';

const StockDetail = () => {
  const { symbol } = useParams();
  
  const safeSymbol = symbol ? decodeURIComponent(symbol).toUpperCase().replace(/[^A-Z0-9-]/g, '') : 'UNKNOWN';

  return (
    <div className="p-8 h-full flex flex-col items-center justify-center text-center">
      <h1 className="text-3xl font-heading font-bold mb-4">Stock Detail: {safeSymbol}</h1>
      <p className="text-tx-secondary">
        Detailed stock analysis, charts, and indicators for {safeSymbol} will be implemented in a future phase.
      </p>
    </div>
  );
};

export default StockDetail;
