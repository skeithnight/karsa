# KARSA CIO Dashboard - UI Design Template & Component System

**Version:** 1.0  
**Design System:** Tailwind CSS v4 + shadcn/ui  
**Target Audience:** Chief Investment Officer  
**Breakpoints:** Desktop (1920px), Tablet (1024px), Mobile (375px)

---

## 1. DESIGN SYSTEM FOUNDATION

### 1.1 Color Palette

```css
/* Primary Colors */
--color-primary-900: #0f172a;
--color-primary-500: #64748b;
--color-primary-50: #f8fafc;

/* Status Colors */
--color-success: #10b981;
--color-warning: #f59e0b;
--color-danger: #ef4444;
--color-info: #3b82f6;

/* Data Colors */
--color-bull: #10b981;
--color-bear: #ef4444;
--color-neutral: #6b7280;
```

### 1.2 Typography

```css
h1 { font-size: 40px; font-weight: 700; }
h2 { font-size: 30px; font-weight: 600; }
h3 { font-size: 24px; font-weight: 600; }
h4 { font-size: 20px; font-weight: 600; }
body { font-size: 16px; font-weight: 400; }
.text-sm { font-size: 14px; }
.text-xs { font-size: 12px; }
.mono { font-family: "Monaco", monospace; }
```

### 1.3 Spacing System

```css
--space-xs: 4px;
--space-sm: 8px;
--space-md: 16px;
--space-lg: 24px;
--space-xl: 32px;
--space-2xl: 48px;
--space-3xl: 64px;
```

---

## 2. COMPONENT SPECIFICATIONS

### 2.1 Portfolio Status Card
- NAV, daily/WTD/YTD returns
- Sharpe ratio, max drawdown
- Active holdings, cash available
- Responsive grid layout
- Monospace for numbers

### 2.2 Risk Traffic Light
- 6 metrics with status indicators
- Green/Amber/Red based on limits
- Percentage to limit calculation
- Interactive (click for details)

### 2.3 Today's Decisions Card
- 3-5 decision cards
- Status badges (APPROVED, PENDING, ALERT)
- Conviction scores with %
- Entry/target prices
- "View Memo" links

### 2.4 Holdings Table
- 12 stocks, sortable columns
- Status, price, entry, target, conviction, size
- Color-coded P&L
- Click row → opens decision card modal

### 2.5 Stock Decision Card Modal
- Full position details
- Analyst consensus scores
- Key metrics table
- Risk factors & mitigation
- Action buttons

### 2.6 Risk Heatmap
- Sector allocation vs mandate
- Correlation matrix
- Concentration (top 5)
- Color scale (green/amber/red)

### 2.7 Performance Attribution
- Waterfall chart (selection, allocation, beta, residual)
- Win rate by analyst type
- Model accuracy metrics

---

## 3. PAGE LAYOUTS

### Main Dashboard
```
Header [Refresh] [Settings]
├─ Portfolio Status Card
├─ Risk Traffic Light
├─ Today's Decisions (3-5 cards)
├─ Holdings Table (12 stocks)
└─ Risk Heatmap + Attribution
```

### Stock Detail Page
```
← Stock: BBCA
├─ [TAB 1: OVERVIEW]
│  ├─ Portfolio snapshot
│  ├─ Performance metrics
│  └─ Holdings & position
├─ [TAB 2: HISTORY]
│  └─ Past 24-month decisions
├─ [TAB 3: ANALYTICS]
│  ├─ Return distribution
│  ├─ Win rate
│  └─ Trade timing
└─ [TAB 4: MEMO & DEBATE]
   ├─ Full investment memo
   ├─ Bull researcher memo
   └─ Bear researcher memo
```

---

## 4. RESPONSIVE DESIGN

### Desktop (1280px+)
- 3-column layouts
- Full tables with all columns
- Real-time charts

### Tablet (768px)
- 2-column layouts
- Condensed tables
- Charts at 70% width

### Mobile (375px)
- 1-column layouts
- Card view instead of tables
- Bottom navigation

---

## 5. INTERACTIVE ELEMENTS

### Hover States
```css
.card:hover {
  background-color: var(--color-primary-50);
  box-shadow: var(--shadow-lg);
  cursor: pointer;
}
```

### Loading States
```
<Skeleton height="200px" />  // Shimmer animation
```

### Error States
```
<ErrorBoundary>
  <p>Unable to load. <button>Retry</button></p>
</ErrorBoundary>
```

---

## 6. DARK MODE

```css
.dark .card {
  background-color: var(--color-primary-900);
  color: var(--color-primary-50);
}
```

---

## 7. ACCESSIBILITY

- ✅ Contrast ratio: 4.5:1 minimum
- ✅ Keyboard navigation: Tab/Enter/Escape
- ✅ Screen reader support
- ✅ Focus states visible (outline: 2px)

---

**Status:** Production-Ready  
**Last Updated:** June 2026

[... Full UI Design continues ...]
