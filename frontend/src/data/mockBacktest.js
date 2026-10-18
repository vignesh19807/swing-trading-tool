/**
 * @file mockBacktest.js
 * @description Phase 1 & 18 mock data — Algorithmic strategy backtesting performance metrics.
 *
 * DATA CONTRACT REFERENCE:
 *   docs/frontend-api-contract.md (Section 3.7)
 *   docs/week14_backtest_result_schema.md
 *   docs/week15_manual_backtest_validation.md
 */

export const mockBacktest = {
  strategy_name: "Trend Momentum (EMA 20/50 + RSI Breakout)",
  period: "1 Year (Aug 2025 – Aug 2026)",
  run_id: "run_tm_2026_08",
  start_date: "2025-08-01",
  end_date: "2026-08-01",
  symbols: ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "SBIN", "LT"],
  initial_capital: 100000,
  final_equity: 128500,
  total_trades: 124,
  closed_trades: 110,
  open_trades: 8,
  invalid_trades: 4,
  incomplete_trades: 2,
  winning_trades: 69,
  losing_trades: 41,
  win_rate: 62.5,
  profit_factor: 1.8,
  total_pl: 28500,
  total_return_pct: 28.5,
  avg_trade_return_pct: 2.3,
  avg_winning_trade_pct: 5.1,
  avg_losing_trade_pct: -2.4,
  max_drawdown: 12.4,
  max_drawdown_pct: 12.4,
  sharpe_ratio: 1.42,
  cagr: 28.5,
  last_updated: new Date().toISOString(),

  // Historical equity time series for valid curve visualization
  equity_curve: [
    { date: "2025-08-01", equity: 100000, drawdown_pct: 0.0 },
    { date: "2025-09-01", equity: 102400, drawdown_pct: 0.0 },
    { date: "2025-10-01", equity: 101150, drawdown_pct: 1.22 },
    { date: "2025-11-01", equity: 89700, drawdown_pct: 12.4 }, // Max Drawdown point
    { date: "2025-12-01", equity: 94800, drawdown_pct: 7.42 },
    { date: "2026-01-01", equity: 104200, drawdown_pct: 0.0 }, // New peak
    { date: "2026-02-01", equity: 108900, drawdown_pct: 0.0 },
    { date: "2026-03-01", equity: 106700, drawdown_pct: 2.02 },
    { date: "2026-04-01", equity: 113400, drawdown_pct: 0.0 },
    { date: "2026-05-01", equity: 117800, drawdown_pct: 0.0 },
    { date: "2026-06-01", equity: 115200, drawdown_pct: 2.21 },
    { date: "2026-07-01", equity: 122600, drawdown_pct: 0.0 },
    { date: "2026-08-01", equity: 128500, drawdown_pct: 0.0 }
  ],

  // Monthly return breakdown
  monthly_returns: [
    { month: "Aug 2025", return_pct: 2.4, trades: 10, win_count: 6 },
    { month: "Sep 2025", return_pct: -1.22, trades: 9, win_count: 4 },
    { month: "Oct 2025", return_pct: -11.32, trades: 12, win_count: 3 },
    { month: "Nov 2025", return_pct: 5.68, trades: 11, win_count: 7 },
    { month: "Dec 2025", return_pct: 9.92, trades: 13, win_count: 9 },
    { month: "Jan 2026", return_pct: 4.51, trades: 8, win_count: 6 },
    { month: "Feb 2026", return_pct: -2.02, trades: 10, win_count: 5 },
    { month: "Mar 2026", return_pct: 6.28, trades: 11, win_count: 8 },
    { month: "Apr 2026", return_pct: 3.88, trades: 9, win_count: 6 },
    { month: "May 2026", return_pct: -2.21, trades: 7, win_count: 3 },
    { month: "Jun 2026", return_pct: 6.42, trades: 10, win_count: 7 },
    { month: "Jul 2026", return_pct: 4.81, trades: 10, win_count: 7 }
  ]
};
