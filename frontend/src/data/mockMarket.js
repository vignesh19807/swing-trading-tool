export const mockMarketIndices = {
  nifty50: {
    value: 25412.30,
    change_percent: 0.72,
    is_positive: true
  },
  sensex: {
    value: 83450.22,
    change_percent: 0.58,
    is_positive: true
  },
  condition: {
    status: "Positive",
    label: "Swing friendly",
    description: "Breadth improving",
    advancing: 1248,
    declining: 724
  }
};

export const mockDataHealth = {
  market_data: "Healthy",
  technical_data: "Healthy",
  financial_data: "Healthy",
  last_updated: new Date().toISOString()
};
