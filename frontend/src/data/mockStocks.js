/**
 * @file mockStocks.js
 * @description Phase 1 & 12 mock data — stock universe list for Indian equities.
 *
 * USAGE RULES:
 *   - Only active when VITE_USE_MOCK_DATA=true
 *   - Never used silently in production
 *
 * DATA CONTRACT REFERENCE:
 *   docs/frontend-api-contract.md (Section 3.3)
 */

export const mockStocks = [
  {
    symbol: "TCS",
    company_name: "Tata Consultancy Services Ltd",
    sector: "Information Technology",
    industry: "IT Services & Consulting",
    current_price: 3520.0,
    change_percent: 1.45,
    opportunity_score: 78.5,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "RELIANCE",
    company_name: "Reliance Industries Ltd",
    sector: "Energy",
    industry: "Oil & Gas Refining",
    current_price: 2940.5,
    change_percent: 0.82,
    opportunity_score: 76.2,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "HDFCBANK",
    company_name: "HDFC Bank Ltd",
    sector: "Banking",
    industry: "Private Sector Bank",
    current_price: 1645.0,
    change_percent: 1.10,
    opportunity_score: 74.8,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "ICICIBANK",
    company_name: "ICICI Bank Ltd",
    sector: "Banking",
    industry: "Private Sector Bank",
    current_price: 1120.0,
    change_percent: 0.65,
    opportunity_score: 73.1,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "INFY",
    company_name: "Infosys Ltd",
    sector: "Information Technology",
    industry: "IT Services & Consulting",
    current_price: 1580.0,
    change_percent: -0.35,
    opportunity_score: 71.5,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "LT",
    company_name: "Larsen & Toubro Ltd",
    sector: "Capital Goods",
    industry: "Heavy Engineering",
    current_price: 3620.0,
    change_percent: 1.90,
    opportunity_score: 70.4,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "BHARTIARTL",
    company_name: "Bharti Airtel Ltd",
    sector: "Telecommunication",
    industry: "Telecom Services",
    current_price: 1315.0,
    change_percent: 0.45,
    opportunity_score: 68.9,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "TATAMOTORS",
    company_name: "Tata Motors Ltd",
    sector: "Automobile",
    industry: "Commercial & Passenger Vehicles",
    current_price: 985.0,
    change_percent: 2.15,
    opportunity_score: 67.2,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "WIPRO",
    company_name: "Wipro Ltd",
    sector: "Information Technology",
    industry: "IT Services & Consulting",
    current_price: 480.5,
    change_percent: -0.75,
    opportunity_score: 64.3,
    recommendation: "WATCH",
    market_status: "Active"
  },
  {
    symbol: "SUNPHARMA",
    company_name: "Sun Pharmaceutical Industries Ltd",
    sector: "Pharmaceuticals",
    industry: "Formulations & Active Ingredients",
    current_price: 1680.0,
    change_percent: 0.20,
    opportunity_score: 62.8,
    recommendation: "WATCH",
    market_status: "Active"
  },
  {
    symbol: "TITAN",
    company_name: "Titan Company Ltd",
    sector: "Consumer Goods",
    industry: "Watches & Jewelry",
    current_price: 3410.0,
    change_percent: -1.20,
    opportunity_score: 61.5,
    recommendation: "WATCH",
    market_status: "Active"
  },
  {
    symbol: "HINDUNILVR",
    company_name: "Hindustan Unilever Ltd",
    sector: "FMCG",
    industry: "Personal & Home Care",
    current_price: 2490.0,
    change_percent: 0.15,
    opportunity_score: 58.0,
    recommendation: "WATCH",
    market_status: "Active"
  },
  {
    symbol: "ITC",
    company_name: "ITC Ltd",
    sector: "FMCG",
    industry: "Diversified FMCG",
    current_price: 465.0,
    change_percent: -0.40,
    opportunity_score: 56.4,
    recommendation: "WATCH",
    market_status: "Active"
  },
  {
    symbol: "KOTAKBANK",
    company_name: "Kotak Mahindra Bank Ltd",
    sector: "Banking",
    industry: "Private Sector Bank",
    current_price: 1780.0,
    change_percent: -0.85,
    opportunity_score: 55.2,
    recommendation: "WATCH",
    market_status: "Active"
  },
  {
    symbol: "MARUTI",
    company_name: "Maruti Suzuki India Ltd",
    sector: "Automobile",
    industry: "Passenger Cars",
    current_price: 12450.0,
    change_percent: 0.95,
    opportunity_score: 65.0,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "AXISBANK",
    company_name: "Axis Bank Ltd",
    sector: "Banking",
    industry: "Private Sector Bank",
    current_price: 1180.0,
    change_percent: 0.30,
    opportunity_score: 63.5,
    recommendation: "WATCH",
    market_status: "Active"
  },
  {
    symbol: "ASIANPAINT",
    company_name: "Asian Paints Ltd",
    sector: "Consumer Goods",
    industry: "Paints & Coatings",
    current_price: 2890.0,
    change_percent: -1.45,
    opportunity_score: 51.0,
    recommendation: "WATCH",
    market_status: "Active"
  },
  {
    symbol: "SBIN",
    company_name: "State Bank of India",
    sector: "Banking",
    industry: "Public Sector Bank",
    current_price: 815.0,
    change_percent: 1.25,
    opportunity_score: 66.8,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "NTPC",
    company_name: "NTPC Ltd",
    sector: "Energy",
    industry: "Power Generation",
    current_price: 395.0,
    change_percent: 0.60,
    opportunity_score: 67.5,
    recommendation: "BUY",
    market_status: "Active"
  },
  {
    symbol: "BAJFINANCE",
    company_name: "Bajaj Finance Ltd",
    sector: "Financial Services",
    industry: "Non-Banking Financial Company",
    current_price: 6850.0,
    change_percent: -2.30,
    opportunity_score: 48.2,
    recommendation: "SELL",
    market_status: "Active"
  }
];
