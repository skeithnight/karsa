---
name: Sovereign Alpha
colors:
  surface: '#131315'
  surface-dim: '#131315'
  surface-bright: '#39393b'
  surface-container-lowest: '#0e0e10'
  surface-container-low: '#1b1b1d'
  surface-container: '#201f21'
  surface-container-high: '#2a2a2c'
  surface-container-highest: '#353437'
  on-surface: '#e5e1e4'
  on-surface-variant: '#c4c7c8'
  inverse-surface: '#e5e1e4'
  inverse-on-surface: '#303032'
  outline: '#8e9193'
  outline-variant: '#444749'
  surface-tint: '#c5c7c8'
  primary: '#ffffff'
  on-primary: '#2e3132'
  primary-container: '#e1e3e4'
  on-primary-container: '#626566'
  inverse-primary: '#5c5f60'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffffff'
  on-tertiary: '#472a00'
  tertiary-container: '#ffddb8'
  on-tertiary-container: '#8d5900'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e1e3e4'
  primary-fixed-dim: '#c5c7c8'
  on-primary-fixed: '#191c1d'
  on-primary-fixed-variant: '#454748'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#131315'
  on-background: '#e5e1e4'
  surface-variant: '#353437'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  body-base:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  stat-lg:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.05em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 24px
  margin-desktop: 24px
  margin-mobile: 16px
---

## Brand & Style

The design system is engineered for high-stakes financial environments where information density and rapid cognitive processing are paramount. It targets Chief Investment Officers (CIOs) and quantitative analysts who require a "mission control" atmosphere to manage complex portfolio data without visual fatigue.

The aesthetic follows a **Corporate / Modern** approach with **Minimalist** and **Glassmorphic** influences. It prioritizes data over decoration, using a dark-mode-first strategy to reduce eye strain. Visual hierarchy is established through meticulous typography and subtle tonal layering rather than aggressive color. The mood is professional, precise, and authoritative, evoking the feeling of a premium Bloomberg terminal filtered through modern UI sensibilities.

## Colors

This design system utilizes a functional palette where color is reserved for state and status rather than branding.

- **Primary (Crisp White):** Reserved for high-priority typography and primary interactive elements.
- **Secondary (Emerald Green):** Indicates positive growth, alpha generation, and "Healthy" system status.
- **Tertiary (Amber):** Used for warnings, pending approvals, or data approaching risk thresholds.
- **Neutral (Deep Charcoal):** The foundation. It uses varying shades of charcoal to define depth without breaking the dark-mode immersion.

Backgrounds utilize `#121214` to provide a true-black baseline, while containers use `#1A1A1E` to lift content. Semantic colors (Emerald, Amber, Red) must maintain high saturation to remain legible against the dark background.

## Typography

The typography system uses a dual-font strategy to separate qualitative narrative from quantitative data.

**Hanken Grotesk** is used for all UI labels, titles, and descriptive text. Its contemporary, sharp geometry ensures clarity even in dense layouts.

**JetBrains Mono** is the engine for all numerical data, currency values, and technical metadata. The monospaced nature is critical for financial tables, allowing numbers to align vertically for rapid ocular scanning. 

- Use **Negative Letter Spacing** on larger headlines to maintain a compact, high-end editorial feel.
- **Tabular figures** must be enabled for all financial readouts to prevent "jumping" during real-time data updates.

## Layout & Spacing

The layout philosophy follows a **Fixed Grid** model on desktop to ensure complex charts maintain their intended aspect ratios, transitioning to a fluid single-column stack on mobile.

- **Grid:** 12-column system with 24px gutters.
- **Density:** High. Standard component padding is 16px (`md`), while data-heavy rows are compressed to 8px (`sm`) or 4px (`xs`) to maximize the information visible "above the fold."
- **Breakpoints:**
  - Desktop: 1200px+ (12 columns)
  - Tablet: 768px (6 columns)
  - Mobile: <768px (1 column)

Vertical rhythm should strictly follow the 4px base unit. Whitespace is used functionally—larger gaps (`xl`) separate distinct modules (e.g., Portfolio Status vs. Holdings), while smaller gaps (`sm`) group related data points.

## Elevation & Depth

Hierarchy is conveyed through **Tonal Layers** and **Low-Contrast Outlines** rather than traditional drop shadows.

- **Level 0 (Background):** `#121214`.
- **Level 1 (Cards/Panels):** `#1A1A1E`. These feature a `1px` solid border using `rgba(255, 255, 255, 0.08)`.
- **Level 2 (Popovers/Modals):** `#242429`. These use a more pronounced border `rgba(255, 255, 255, 0.15)` and a subtle `backdrop-blur` (8px) to separate the element from the dashboard grid.

Shadows, if used for modals, must be ultra-diffused: `0 20px 40px rgba(0,0,0,0.4)`. The overall goal is to create a sense of "etched" panels on a glass surface.

## Shapes

The shape language is **Rounded** to soften the technical nature of the data. 

- **Containers & Cards:** 0.75rem (`rounded-lg`) to provide a clear frame for charts.
- **Buttons & Inputs:** 0.5rem (`rounded-md`) for a precise, clickable appearance.
- **Status Pills:** Fully rounded (`rounded-full`) to distinguish them from interactive buttons.

This moderate roundedness balances modern software aesthetics with the rigid structure of financial data grids.

## Components

### Buttons
- **Primary:** Background primary (White), text neutral (Charcoal). High contrast for main actions.
- **Ghost:** No background, border `rgba(255,255,255,0.1)`. Used for secondary navigation or "View More" actions.
- **Scale:** On click, buttons should slightly scale down (98%) to provide tactile feedback.

### Data Tables (The Core)
- **Header Row:** Background `#1E1E22`, Geist Mono (Bold, 11px), All-Caps.
- **Cells:** Right-aligned for numbers, left-aligned for text. Row height 40px (Dense).
- **Zebra Striping:** Use subtle variations in background color for alternating rows to aid readability.

### Status Indicators
- **Glow Effect:** Status dots (Emerald/Amber) should feature a subtle outer glow (2px blur) of the same color to simulate hardware LEDs.

### Cards
- Every card must have a header section containing a title (Hanken Grotesk) and an optional "More" icon. 
- Padding should be consistent at `16px` unless the card contains a full-bleed table.

### Input Fields
- Dark-themed inputs with `#1A1A1E` background.
- Focus state: Border color changes to primary (White) with a 2px outer ring of `rgba(255,255,255,0.1)`.