# AUDIT-009: Browser & Route Verification

## 1. Registered Route Inventory

From `frontend/src/App.jsx`, the application registers 8 client-side routes wrapped in `MainLayout`:

| Route Path | React Component File | Stated Purpose | HTTP Status Probe | Browser Automation |
|---|---|---|:---:|:---:|
| `/` | `src/pages/Dashboard.jsx` | Executive summary, market overview, top opportunities | HTTP 200 | **NOT TESTED (CLI env)** |
| `/opportunities` | `src/pages/Opportunities.jsx` | Full opportunity ranking table with filters | HTTP 200 | **NOT TESTED (CLI env)** |
| `/stocks` | `src/pages/StockExplorer.jsx` | Universe screener, searchable 52-stock table | HTTP 200 | **NOT TESTED (CLI env)** |
| `/stocks/:symbol` | `src/pages/StockDetail.jsx` | Single stock deep dive, OHLC chart, technical/financial tabs | HTTP 200 | **NOT TESTED (CLI env)** |
| `/sectors` | `src/pages/SectorExplorer.jsx` | Sector relative strength and performance ranking | HTTP 200 | **NOT TESTED (CLI env)** |
| `/performance` | `src/pages/Performance.jsx` | Portfolio backtest metrics and equity curve chart | HTTP 200 | **NOT TESTED (CLI env)** |
| `/watchlist` | `src/pages/Watchlist.jsx` | User-curated stocks stored in browser LocalStorage | HTTP 200 | **NOT TESTED (CLI env)** |
| `*` | `src/pages/NotFound.jsx` | 404 fallback page | HTTP 200 | **NOT TESTED (CLI env)** |

---

## 2. Browser Automation Tooling Audit (Phase 6 Compliance)

In strict accordance with the AUDIT-009 Phase 6 directive:
> *"Use browser automation if available. Do not describe a route as browser-tested based solely on unit tests, source-code inspection, or a successful HTTP response. If browser automation is unavailable, state the limitation and do not claim end-to-end verification."*

### Tooling Check:
* Playwright CLI / Python library: **Not installed**
* Puppeteer Node module: **Not installed**
* Selenium WebDriver: **Not installed**
* Chrome Headless CLI driver: **Not installed**

### Verification Method Executed:
1. **Network Layer:** Both frontend dev server (`http://127.0.0.1:5173`) and backend API (`http://127.0.0.1:8000`) were proven active and serving requests with HTTP 200 OK.
2. **Production Bundler:** Vite 8 production build transformed all 8 routes without syntax or bundling errors.
3. **Automated Unit Testing of Route Logic:**
   - Screener filtering and sorting logic: Verified via `screenerFilters.test.js` (53 tests).
   - Sector explorer calculations: Verified via `sectorHelpers.test.js` (56 tests).
   - Performance metrics and chart data mapping: Verified via `performanceHelpers.test.js` (46 tests).
   - Watchlist LocalStorage lifecycle: Verified via `watchlistStorage.test.js` (49 tests).
   - Dashboard regression issues: Verified via `dashboardRegressions.test.js` (10 tests).
4. **Explicit Limitation Disclosure:**
   Visual rendering in a real browser viewport (e.g. mobile 390x844 responsive layout inspection, DOM element screenshot capture) **could not be executed automatically** due to the absence of a browser automation driver in the local environment. It is therefore documented as **PASS (BUILD & LOGIC) / BLOCKED (HEADLESS DRIVER UNAVAILABLE)** rather than fabricating false browser execution logs.

