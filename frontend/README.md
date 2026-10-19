# Swing-tool — Frontend Platform

> **Systematic Swing Trading Intelligence & Technical Screening Platform for Indian Equities (NSE)**

Swing-tool is a high-performance web dashboard built with **React 19**, **Vite**, **Tailwind CSS v4**, and **React Router v7**. It equips swing traders with algorithmic trade setups, multi-timeframe relative strength screening, risk/reward calculations, and performance metrics.

---

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Development Workflow](#development-workflow)
- [Configuration & Environment Variables](#configuration--environment-variables)
  - [Mock Mode vs Real API Mode](#mock-mode-vs-real-api-mode)
  - [Security Rules](#security-rules)
- [Available Routes](#available-routes)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Production Build & Optimization](#production-build--optimization)
- [Deployment & SPA History Fallback](#deployment--spa-history-fallback)
- [Current Limitations & Roadmap](#current-limitations--roadmap)

---

## Features

- **Market Intelligence Dashboard (`/`)**: Real-time regime assessment, benchmark tracking (NIFTY 50, NIFTY Bank, India VIX), top swing opportunities, and sector leadership.
- **Swing Opportunity Screener (`/opportunities`)**: Algorithmic technical rankings, entry/target/stop-loss recommendations, and risk/reward ratios.
- **Stock Explorer (`/stocks`)**: Fast filtering and search across all tracked equities with setup criteria and indicators.
- **Stock Detail View (`/stocks/:symbol`)**: Deep-dive technical view with SVG price charts, EMA overlays (20/50/200), RSI & MACD oscillators, and interactive trade cards.
- **Sector Explorer (`/sectors`)**: Multi-timeframe relative strength (21d, 63d, 126d) categorizing outperforming, in-line, and lagging sectors with constituent drill-downs.
- **Watchlist Tracker (`/watchlist`)**: Client-side localStorage persistence with tracking of prices since addition, gainers/decliners breakdown, and average return metrics.
- **Performance Analytics (`/performance`)**: System equity curve visualizer, win rate, profit factor, max drawdown, and monthly returns heatmap.
- **Theme Support**: Seamless Dark/Light mode switching.

---

## Prerequisites

- **Node.js**: `v18.0.0` or higher (verified on Node `v24.x`).
- **npm**: `v9.0.0` or higher.

---

## Installation

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install all dependencies:
   ```bash
   npm install
   ```

3. Set up your local environment file:
   ```bash
   cp .env.example .env.local
   ```

---

## Development Workflow

### Starting the Dev Server
```bash
npm run dev
```
Starts the Vite development server with Hot Module Replacement (HMR) at `http://localhost:5173`.

### Running Tests
```bash
npm test
```
Runs the zero-dependency test suite (`node src/utils/run_all_tests.js`) covering:
- Watchlist storage, normalization, duplicate protection, and filtering.
- Performance helper math, equity curve scale calculation, and drawdown logic.
- Sector relative strength parsing, classification, and ranking.
- Screener filtering and technical indicators (EMA, RSI, MACD).

### Code Quality & Linting
```bash
npm run lint
```
Runs Oxlint across all JSX/JS files.

---

## Configuration & Environment Variables

Environment variables are managed using Vite's `import.meta.env` system.

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | String | `http://localhost:5000` | Base URL of the backend REST API service. |
| `VITE_USE_MOCK_DATA` | String (`"true"` \| `"false"`) | `"false"` | When `"true"`, the frontend serves bundled mock fixtures for offline development. |

### Mock Mode vs Real API Mode

#### 1. Running in Mock Mode (Offline Development)
Set the following in `.env.local`:
```env
VITE_USE_MOCK_DATA=true
VITE_API_BASE_URL=http://localhost:5000
```
- In Mock Mode, `src/services/api.js` dynamically loads data from `src/data/mock*.js`.
- The frontend operates completely independently without requiring a backend server or database.

#### 2. Running in Real API Mode (Production & Integration)
Set the following in `.env.local` or your hosting environment:
```env
VITE_USE_MOCK_DATA=false
VITE_API_BASE_URL=https://api.yourdomain.com
```
- **Failsafe Error Handling**: If `VITE_USE_MOCK_DATA` is `false` (or omitted) and `VITE_API_BASE_URL` is not defined, `src/services/api.js` explicitly throws:
  ```
  Configuration Error: VITE_API_BASE_URL is missing. Real API mode requires this environment variable.
  ```
- The frontend **never silently falls back to mock data** when configured for real API mode. All pages capture this error and display a clear, actionable `ErrorState` notification.

### Security Rules
- **No Secrets in Frontend**: Any variable prefixed with `VITE_` is baked directly into client-side JS bundles. Never place API keys, private tokens, database credentials, or passwords in frontend environment files.
- `.env.local` and `.env.*.local` are strictly `.gitignore`d and must not be committed to version control.

---

## Available Routes

| Route | Page Component | Description |
| :--- | :--- | :--- |
| `/` | `Dashboard` | Market overview, top swing ideas, sector trends, market regime. |
| `/opportunities` | `Opportunities` | Ranked opportunity screener with filters for strategy and score. |
| `/stocks` | `StockExplorer` | Equities screener with live filtering and metrics. |
| `/stocks/:symbol` | `StockDetail` | Detailed technical analysis for a symbol (e.g. `/stocks/ASIANPAINT`). |
| `/sectors` | `SectorExplorer` | Sector performance and 21d/63d/126d relative strength analysis. |
| `/watchlist` | `Watchlist` | User watchlist with price tracking and performance attribution. |
| `/performance` | `Performance` | Strategy analytics, equity curves, drawdown, and monthly returns. |
| `/settings` | `PlaceholderPage` | Application settings (planned for future phase). |
| `/data-health` | `PlaceholderPage` | Data pipeline freshness and health (planned for future phase). |
| `*` | `NotFound` | 404 page with return-to-dashboard navigation. |

---

## Testing & Quality Assurance

The frontend includes unit tests that run directly via Node.js:
- `watchlistStorage.test.js` — 49 tests
- `performanceHelpers.test.js` — 46 tests
- `sectorHelpers.test.js` — 56 tests
- `screenerFilters.test.js` — 27 tests
- `technicalIndicators.test.js` — 32 tests

Execute all tests anytime with:
```bash
npm test
```

---

## Production Build & Optimization

To compile the application for production:
```bash
npm run build
```

Build outputs are generated in `frontend/dist/`.

### Optimizations Included
- **Vendor Chunk Splitting**: Configured in `vite.config.js` via Rolldown/Rollup manual chunking:
  - `vendor-react`: Bundles `react`, `react-dom`, `react-router-dom` (~207 kB).
  - `vendor-icons`: Bundles `lucide-react` (~16 kB).
  - `index`: Application core logic and UI components (~334 kB).
- **Dynamic Mock Splitting**: Mock datasets (`src/data/mock*.js`) are loaded only when `VITE_USE_MOCK_DATA=true` via dynamic `import()`, preventing mock data from bloating the primary bundle.
- **Production Source Maps**: Source maps are disabled by default in production builds to prevent exposing source code and sensitive details.

### Testing the Production Build Locally
```bash
npm run preview
```
Starts a local static server serving `dist/` at `http://localhost:4173`.

---

## Deployment & SPA History Fallback

Because Swing-tool is a Single-Page Application (SPA) using React Router's HTML5 History API, all direct navigations and page refreshes (such as refreshing `/stocks/ASIANPAINT` or navigating directly to `/opportunities`) must be rewritten by the host server to serve `/index.html`.

### Host Configuration Examples

#### Nginx
```nginx
server {
    listen 80;
    server_name swing-tool.example.com;
    root /var/www/swing-tool/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### Apache (`.htaccess` in `dist/`)
```apache
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteBase /
  RewriteRule ^index\.html$ - [L]
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteRule . /index.html [L]
</IfModule>
```

#### Netlify
Create `public/_redirects` (or configure `netlify.toml`):
```text
/*    /index.html   200
```

#### Vercel
Add `vercel.json` in the frontend root:
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

#### AWS S3 + CloudFront
Configure CloudFront **Custom Error Responses**:
- HTTP Error Code: `403` and `404`
- Response Page Path: `/index.html`
- HTTP Response Code: `200`

---

## Current Limitations & Roadmap

- **Live Backend Integration**: The current frontend release is wired to the `src/services/api.js` contract. Live backend integration and authorization header wiring is scheduled for the subsequent backend integration phase.
- **Placeholder Pages**: `/settings` and `/data-health` routes display informative placeholder screens describing planned roadmap features.
