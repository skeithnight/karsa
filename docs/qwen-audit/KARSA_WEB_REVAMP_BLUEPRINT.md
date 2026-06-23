# Karsa-Web Revamp Blueprint: From Web App to Institutional Terminal

**Target:** `karsa-web/` (Next.js Frontend)  
**Persona:** Professional IDX Portfolio Manager / Lead Trader  
**Goal:** Complete UI/UX and architectural revamp to support high-frequency data, dense information display, and IDX-specific risk oversight.

---

## 1. Executive Summary & Current State Audit

### The "As-Is" Audit (Typical Early-Stage Next.js App)
While the current `karsa-web` has a solid foundation (Next.js App Router, Tailwind, basic AG Grid), it suffers from "startup UI syndrome" which is fatal for a trading desk:
*   **Too Much Whitespace:** Standard shadcn/ui components use large paddings and fonts. In trading, screen real estate is money.
*   **Retail-Looking Charts:** Standard line charts do not convey volume, volatility, or order flow.
*   **Passive Data Loading:** Relies on standard REST polling. Fails to leverage the WebSocket infrastructure built in Sprint 59 for true real-time updates.
*   **Missing IDX Context:** Displays raw numbers without proper IDR formatting, ignores IDX lot sizes (1 lot = 100 shares), and lacks visual grouping for local conglomerates.

### The Vision for the Revamp
We are rebuilding `karsa-web` to be a **Command Center**. 
*   **Density over Decoration:** Compact rows, monospaced numbers, minimal borders.
*   **Real-Time by Default:** The UI is a live reflection of the backend Event Store via WebSockets.
*   **Action-Oriented:** Every screen allows the PM to drill down, approve, reject, or halt trading without leaving the keyboard.

---

## 2. The New Tech Stack & Architecture

To handle the revamp, we must upgrade the frontend tooling to handle heavy data rendering without blocking the main thread.

| Layer | Current / Standard | **Revamp Target (Institutional Grade)** |
| :--- | :--- | :--- |
| **Framework** | Next.js 14 (App Router) | **Next.js 14+** (Keep, but strict Client/Server component separation). |
| **State Management** | React Context / Prop drilling | **Zustand** (for global UI state) + **TanStack Query** (for REST) + **Native WebSocket hooks** (for live ticks). |
| **Data Grids** | Basic AG Grid | **AG Grid Enterprise** (Must use Server-Side Row Model, Custom Cell Renderers, and Clipboard integration). |
| **Charting** | Recharts / Chart.js | **TradingView Lightweight Charts** (for price/OHLCV) + **Nivo** or **D3** (for complex portfolio heatmaps/exposures). |
| **Styling** | Tailwind + shadcn/ui | **Tailwind + Custom Trading Theme** (Strict dark mode, monospaced fonts for numbers, high-contrast semantic colors). |
| **Forms/Inputs** | Standard HTML inputs | **React Hook Form + Zod** (Strict validation for order tickets and risk overrides). |

---

## 3. Core Modules to Rebuild (The "To-Be" Architecture)

The revamp is divided into four distinct workspaces, accessible via a persistent left-hand navigation rail.

### Workspace 1: The CIO Command Center (Dashboard)
*The "Forest" View. What the PM looks at 80% of the time.*

*   **Top Ticker Tape (Sticky Header):** 
    *   Live IHSG (JCI) index, USD/IDR exchange rate, and 10Y Indo Gov Bond yield.
    *   *Crucial:* Current Portfolio Equity (IDR), Daily PnL (IDR & %), Cash Drag %.
*   **Main Panel (Left 60%):** 
    *   **Equity Curve:** TradingView Lightweight Chart. Shows portfolio value over time. Overlays the IHSG benchmark to show Alpha.
    *   **Drawdown Chart:** Area chart showing underwater equity (peak-to-trough decline).
*   **Right Panel (40%):**
    *   **Live Event Feed:** A scrolling, color-coded timeline of `OrderFilledEvent`, `ThesisApprovedEvent`, and `StaleDataAlertEvent`.
    *   **Risk Gauges:** Visual speedometers for Portfolio VaR, Gross/Net Exposure, and Max Drawdown.

### Workspace 2: The Thesis & Execution Hub
*The "Trees" View. Where the PM reviews AI signals and manages orders.*

*   **The AG Grid (Takes up 80% of screen):**
    *   *Columns:* Ticker, Company Name, AI Conviction (0-1 visual bar), Side (BUY/SELL), Target Size (Lots), Current Price (IDR), Stop Loss, Take Profit, Status (Generated/Approved/Executed).
    *   *Custom Renderers:* Conviction score rendered as a green/red progress bar. Status rendered as a pill badge.
    *   *Context Menu:* Right-click a row to "Force Approve", "Reject", or "View AI Reasoning".
*   **Slide-out Drawer (The "Brain" View):**
    *   When a row is clicked, a drawer slides out from the right showing the **Immutable Decision Ledger**.
    *   Shows the exact LLM prompt, the RAG context retrieved (past post-mortems), and the Governance Agent's JSON validation.

### Workspace 3: IDX Risk & Conglomerate Console (NEW)
*The "Survival" View. Specific to the Indonesian market.*

*   **Conglomerate Heatmap:** A Treemap showing exposure grouped by local groups (Prajogo, Sinar Mas, Astra, Bakrie, Salim). If TPIA and BREN are both 10% of the book, the "Prajogo" block glows red, showing 20% correlated risk.
*   **Macro Circuit Breaker Status:** 
    *   Live tracking of USD/IDR. Visual indicator if the >2% or >5% weekly drop triggers are approaching.
    *   MSCI Rebalance countdown and free-float warnings for specific tickers.
*   **Sector Exposure Bar Chart:** Gross vs. Net exposure by IDX sector (Financials, Basic Materials, Consumer, etc.).

### Workspace 4: The Post-Mortem & Calibration Lab
*The "Learning" View.*

*   **Brier Score Calibration Curve:** A scatter plot showing AI Conviction Score (X-axis) vs. Actual Win Rate (Y-axis). If the dots don't form a straight line, the AI needs recalibration.
*   **Brinson Attribution Table:** AG Grid breaking down monthly returns into: Asset Allocation, Stock Selection, and Beta/Market effect.
*   **Failure Regime Tracker:** A list of all `ThesisRejectedEvent` and losing trades, tagged with the AI's reasoning vs. what actually happened.

---

## 4. UX/UI Design Rules for the Revamp

To ensure the frontend feels like a professional tool, enforce these strict design rules:

1.  **Monospaced Numbers:** All financial data (prices, PnL, sizes) **must** use a monospaced font (e.g., `JetBrains Mono` or `Roboto Mono`). This ensures decimal points align vertically in the AG Grid, allowing the eye to scan columns instantly.
2.  **Semantic Color Palette:** 
    *   Backgrounds: Deep charcoal/dark grey (not pure black, reduces eye strain).
    *   Text: Off-white/light grey.
    *   **Data Colors:** Green (`#00C853`) for Profit/Long/Bullish. Red (`#FF3D00`) for Loss/Short/Bearish. Yellow/Amber (`#FFB300`) for Warnings/Stale Data. *Never use color for decoration.*
3.  **Compact Density:** AG Grid row height must be set to `24px` or `28px`. Remove excessive padding. A PM needs to see 50 tickers on one screen, not 15.
4.  **Keyboard First:** 
    *   `Cmd/Ctrl + K`: Global search (Jump to ticker, jump to page).
    *   `J / K`: Navigate up/down in AG Grid.
    *   `Enter`: Open details drawer.
    *   `Esc`: Close drawer/modal.

---

## 5. Real-Time Data Flow (The WebSocket Revamp)

The current UI likely fetches data on page load. The revamp must implement a robust WebSocket architecture.

```typescript
// hooks/useKarsaWebSocket.ts
export function useKarsaWebSocket() {
  const [state, setState] = useZustandStore(); // Global state
  
  useEffect(() => {
    const ws = new WebSocket('wss://api.karsa.local/api/cio/ws/live');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Route events to specific state slices
      switch(data.type) {
        case 'portfolio_update':
          setState('equity', data.total_equity);
          setState('pnl', data.daily_pnl);
          break;
        case 'thesis_generated':
          // Optimistically update the AG Grid without full re-render
          gridApi.applyTransaction({ add: [data.thesis] }); 
          break;
        case 'stale_data_alert':
          // Trigger full-screen UI overlay
          setState('isHalted', true);
          break;
      }
    };
    
    return () => ws.close();
  }, []);
}
```

---

## 6. Execution Plan: How to Revamp

Do not try to rewrite everything at once. Use a phased approach:

### Phase 1: The Design System & Shell (Days 1-3)
- Set up the new Tailwind config (Dark mode, monospaced fonts, semantic colors).
- Build the persistent layout (Left nav rail, sticky top ticker tape).
- Implement the WebSocket hook and Zustand state management.

### Phase 2: The CIO Command Center (Days 4-7)
- Build the top banner (Equity, PnL, Cash).
- Integrate TradingView Lightweight Charts for the Equity Curve.
- Connect the live event feed via WebSocket.

### Phase 3: The Thesis Hub & AG Grid (Days 8-12)
- Configure AG Grid Enterprise with Server-Side Row Model.
- Build custom cell renderers (Conviction bars, Status pills).
- Build the slide-out drawer for the Immutable Decision Ledger.

### Phase 4: IDX Risk & Post-Mortem (Days 13-16)
- Build the Conglomerate Heatmap (Treemap).
- Implement the Brier Score calibration chart.
- Add the Macro Circuit Breaker visual indicators.

### Phase 5: Polish & Keyboard Navigation (Days 17-20)
- Implement `Cmd+K` search.
- Add Vim-like navigation (`j/k/enter/esc`).
- Performance audit: Ensure the UI doesn't lag when 1,000+ events hit the WebSocket per second.

---

## 7. Final Sign-Off

By executing this revamp, `karsa-web` will transition from a "cool AI project dashboard" into a **lethal, institutional-grade IDX trading terminal**. It will respect the PM's time, highlight the unique risks of the Indonesian market (conglomerates, macro triggers), and provide absolute transparency into the AI's decision-making process.
```

### 💡 Next Steps for You:
1. **Share this with your Frontend Engineer:** This document gives them the exact tech stack, design rules, and module breakdown they need to start scaffolding the new `karsa-web`.
2. **Focus on AG Grid:** If you are using AG Grid, make sure you have the **Enterprise** license (or use the free version if budget is tight, but you'll miss some advanced features). For a trading terminal, AG Grid is non-negotiable.
3. **Get the TradingView Charts:** Go to the TradingView Lightweight Charts documentation. It is free, open-source, and looks exactly like professional trading platforms out of the box.