import React from 'react';

const PlaceholderPage = ({ title }) => {
  return (
    <div className="p-8 h-full flex flex-col items-center justify-center text-center">
      <h1 className="text-3xl font-heading font-bold mb-4">{title}</h1>
      <p className="text-tx-secondary">This page is planned but not yet implemented in this phase.</p>
    </div>
  );
};

export default PlaceholderPage;
