/**
 * @file index.js
 * @description Charts directory barrel file.
 *
 * Phase 2+ will export chart components from here.
 *
 * Planned chart components:
 *   - PriceChart       (OHLCV candlestick / line chart)
 *   - ScoreRadar       (opportunity score radar/spider chart)
 *   - SectorHeatmap    (sector performance heatmap)
 *   - BacktestChart    (performance equity curve)
 *
 * ARCHITECTURE NOTE:
 *   Charts receive pre-fetched, pre-transformed data as props.
 *   They must NOT call the API service directly.
 *   Data fetching belongs in pages or custom hooks (src/hooks/).
 */

// Phase 2+ exports will be added here.
