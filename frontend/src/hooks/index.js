/**
 * @file index.js
 * @description Hooks directory barrel file.
 *
 * Phase 2+ will export custom React hooks from here.
 *
 * Planned custom hooks:
 *   - useOpportunities()   wraps getOpportunities() with loading/error state
 *   - useStock(symbol)     wraps getStock(symbol) with loading/error state
 *   - useSectors()         wraps getSectors() with loading/error state
 *   - useMarketIndices()   wraps getMarketIndices() with loading/error state
 *   - useBacktest()        wraps getLatestBacktest() with loading/error state
 *
 * ARCHITECTURE NOTE:
 *   Hooks consume src/services/api.js — they must not call fetch() directly.
 *   Pages and components consume hooks — they must not call api.js directly.
 */

// Phase 2+ exports will be added here.
