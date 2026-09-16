---
name: SRS Guardian
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45474c'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#75777d'
  outline-variant: '#c5c6cd'
  surface-tint: '#545f73'
  primary: '#091426'
  on-primary: '#ffffff'
  primary-container: '#1e293b'
  on-primary-container: '#8590a6'
  inverse-primary: '#bcc7de'
  secondary: '#4b41e1'
  on-secondary: '#ffffff'
  secondary-container: '#645efb'
  on-secondary-container: '#fffbff'
  tertiary: '#1e1200'
  on-tertiary: '#ffffff'
  tertiary-container: '#35260c'
  on-tertiary-container: '#a38c6a'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e3fb'
  primary-fixed-dim: '#bcc7de'
  on-primary-fixed: '#111c2d'
  on-primary-fixed-variant: '#3c475a'
  secondary-fixed: '#e2dfff'
  secondary-fixed-dim: '#c3c0ff'
  on-secondary-fixed: '#0f0069'
  on-secondary-fixed-variant: '#3323cc'
  tertiary-fixed: '#fadfb8'
  tertiary-fixed-dim: '#ddc39d'
  on-tertiary-fixed: '#271902'
  on-tertiary-fixed-variant: '#564427'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  metric-display:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.005em
  body-base:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-compact:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  label-text:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-caption:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  code-base:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  code-compact:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.01em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system serves a technical, precision-driven audit workspace engineered for software architects, business analysts, and quality leads. The brand personality is calm, analytical, authoritative, and unobtrusive. The interface recedes entirely into the background to spotlight requirement text, structural ambiguities, and rule violations.

### Design Movement & Guiding Tenets
The design movement is **Technical Minimalism** combined with structured **Data Density** (drawing direct inspiration from Linear, GitHub, and the Vercel console).

- **Quiet by Default:** Color signifies triage status or interaction affordance, never decoration. Surfaces remain quiet, neutral, and flat.
- **Architectural Rigor:** Visual hierarchy relies on weight shifts, tabular alignments, and structural 1px hairline rules rather than spatial drop shadows or colorful backgrounds.
- **Zero Theatrics:** Absolute prohibition against gradients, glow states, glassmorphism, decorative blurs, skewed angles, or skeuomorphic bevels.
- **Density with Air:** Component heights are compact (32px inputs, 36px table rows), but content zones utilize clean outer margins and strict alignment grids to prevent cognitive overload during multi-hour review cycles.

## Colors

The palette employs a slate-zinc neutral scale designed to maintain crisp structural readability across varied display calibrations. The primary interaction color is a grounded, deep slate (`#1E293B`) paired with a functional indigo accent (`#4F46E5`) reserved strictly for active navigation items, focus states, and primary trigger events.

### Theme Modes

#### Light (Default Canvas)
- **Canvas / App Background:** `#F8FAFC`
- **Surface / Card Background:** `#FFFFFF`
- **Surface Subdued / Wells:** `#F1F5F9`
- **Border Default:** `#E2E8F0`
- **Border Strong / Interactive:** `#CBD5E1`
- **Text Primary:** `#0F172A`
- **Text Secondary:** `#334155`
- **Text Muted / Placeholder:** `#64748B`

#### Dark Companion Mode
- **Canvas / App Background:** `#0B0F17`
- **Surface / Card Background:** `#111827`
- **Surface Subdued / Wells:** `#1F2937`
- **Border Default:** `#1E293B`
- **Border Strong / Interactive:** `#334155`
- **Text Primary:** `#F8FAFC`
- **Text Secondary:** `#CBD5E1`
- **Text Muted / Placeholder:** `#64748B`

### Semantic Triage Tokens
Semantic colors are strictly restrained to indicators, badges, inline tags, and 1px edge borders. They must **never** be applied as high-saturation flood fills.

- **Critical / High Severity:** Text `#DC2626`, Background `#FEF2F2`, Border `#FECACA` (Dark: Text `#F87171`, Background `#450A0A`, Border `#7F1D1D`)
- **Medium Severity / Warning:** Text `#D97706`, Background `#FFFBEB`, Border `#FDE68A` (Dark: Text `#FBBF24`, Background `#451A03`, Border `#78350F`)
- **Low Severity / Information:** Text `#2563EB`, Background `#EFF6FF`, Border `#BFDBFE` (Dark: Text `#60A5FA`, Background `#172554`, Border `#1E40AF`)
- **Resolved / Compliant:** Text `#16A34A`, Background `#F0FDF4`, Border `#BBF7D0` (Dark: Text `#4ADE80`, Background `#052E16`, Border `#14532D`)

## Typography

The type system prioritizes micro-legibility and horizontal budget conservation.

### Font Configurations & OpenType Rules
- **Prose & Standard UI:** `Inter` set with optical sizing enabled.
- **Requirement IDs, Schemas, & Metric Values:** `JetBrains Mono` for requirement tokens (`REQ-AUTH-012`), schema parameters, code diffs, and lint rule IDs.
- **Tabular Numerals:** All metric callouts, verification percentages, row indices, and status counters must strictly enforce `font-variant-numeric: tabular-nums`.

### Scale & Application
Hierarchy is achieved through font weight (400 regular, 500 medium, 600 semibold) rather than oversized dimensions. The standard body interface runs at `13px` or `14px`. Section headlines do not exceed `20px`. The single display level (`28px`) is reserved solely for high-level health scoreboards and summary metrics.

## Layout & Spacing

This design system uses a strict 4px horizontal and vertical baseline rhythm (`0.25rem` steps). Layouts utilize full-width engineering real estate rather than narrow centered blocks.

### App Shell Architecture
- **Navigation Sidebar:** Persistent `240px` left panel, collapsible to a rigid `52px` icon rail. Uses a flat background with a 1px solid vertical border (`#E2E8F0`).
- **Utility Header:** Fixed `48px` top bar containing document breadcrumbs, live review status, fast filter pills, and utility actions.
- **Primary Canvas:** Fluid multi-column workspace filling remaining viewport space.
- **Inspection Flyout / Split View:** Optional `400px` to `480px` right panel for side-by-side parsing of raw SRS text against automated quality flags.

### Responsive Behavior & Breakpoints
- **Desktop Wide (>= 1440px):** Full 3-pane visibility (Sidebar, Main Data Table / Analysis Canvas, Right Inspection Rail).
- **Desktop Standard (1024px - 1439px):** Inspection Rail defaults to an overlay drawer; sidebar remains pinned at 240px.
- **Tablet / Small Viewports (< 1024px):** Sidebar collapses to 52px icon rail. Data table shifts secondary columns (e.g., "Assigned Lead", "Detected Rules") to expandable row drawers.

## Elevation & Depth

This design system completely discards ambient blurs, fuzzy colored drop shadows, and multi-stop gradients. Depth is established purely through **tonal layering**, **structural nesting**, and **1px crisp hairline borders**.

### Layering Rules
- **Base Canvas (Level 0):** `#F8FAFC`. Houses the application layout shell, outer workspace borders, and background tracks.
- **Panel Surface (Level 1):** `#FFFFFF`, bound by a 1px solid border (`#E2E8F0`). Used for primary data cards, active analysis views, metric summaries, and tables.
- **Interactive Surface / Hover (Level 2):** `#F1F5F9`. Applied to selected table rows, hover states of list items, and active input containers.
- **Floating Overlays / Modals / Menus (Level 3):** `#FFFFFF` with a crisp 1px border (`#CBD5E1`) and a minimal, tight mechanical shadow: `box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05), 0 4px 12px 0 rgba(0, 0, 0, 0.04)`.

## Shapes

The shape vocabulary uses compact, disciplined corner rounding. Pill shapes and organic curves are excluded to maintain an intentional, tool-like aesthetic.

- **Base Radius (4px - `rounded`):** Default for buttons, text inputs, dropdown triggers, inline badges, issue chips, and table cells.
- **Structural Radius (6px to 8px - `rounded-md`):** Applied strictly to larger cards, metric containers, code review blocks, and modal dialogs.
- **Strict Geometric Bounds:** Internal divider borders, split panes, and sticky table header strips always use `0px` radius along their docking edges.

## Components

### Buttons
- **Height & Radius:** `32px` standard height (`28px` for dense table actions), `4px` corner radius.
- **Primary:** Background `#1E293B`, Text `#FFFFFF`, Border 1px solid `#0F172A`. Hover: `#334155`.
- **Secondary / Outline:** Background `#FFFFFF`, Text `#0F172A`, Border 1px solid `#E2E8F0`. Hover: `#F8FAFC`, Border `#CBD5E1`.
- **Ghost:** Background `transparent`, Text `#334155`, Border none. Hover: `#F1F5F9`.
- **Destructive:** Background `#FFFFFF`, Text `#DC2626`, Border 1px solid `#FECACA`. Hover: `#FEF2F2`.
- **Focus State:** 2px ring offset with `outline: 2px solid #4F46E5`.

### Badges & Severity Chips
- **Geometry:** Height `20px`, padding `0 6px`, radius `4px`, font size `11px`, font family `JetBrains Mono` or `Inter Medium`.
- **Execution:** Crisp 1px border matching the text tint, faint background tint. Never use high-contrast filled blobs.
  - *Critical:* BG `#FEF2F2`, Text `#DC2626`, Border `#FECACA`
  - *Medium:* BG `#FFFBEB`, Text `#D97706`, Border `#FDE68A`
  - *Low:* BG `#EFF6FF`, Text `#2563EB`, Border `#BFDBFE`
  - *Resolved:* BG `#F0FDF4`, Text `#16A34A`, Border `#BBF7D0`
  - *Draft / Neutral:* BG `#F1F5F9`, Text `#475569`, Border `#E2E8F0`

### Data Tables
- **Header:** Height `32px`, background `#F8FAFC`, border-bottom `1px solid #CBD5E1`. Font: `Inter`, 11px uppercase, letter-spacing `0.05em`, color `#64748B`. Sticky positioning during document scrolling.
- **Rows:** Height `36px` to `40px` (standard), border-bottom `1px solid #E2E8F0`. Hover: `#F8FAFC`.
- **Selected State:** Background `#F1F5F9` with a 2px left accent border `#4F46E5`.
- **Numeric & ID Alignment:** Requirement codes (`REQ-084`) and numerical indices are left-aligned in `JetBrains Mono`. Scores, counts, and dates are right-aligned using `tabular-nums`.

### Form Inputs & Filters
- **Dimensions:** Height `32px`, font size `13px`, padding `0 10px`, radius `4px`.
- **Normal:** Background `#FFFFFF`, Border 1px solid `#E2E8F0`, Text `#0F172A`.
- **Focus:** Border `#4F46E5`, outline `1px solid #4F46E5`.
- **Search & Filter Bars:** Full-width flat input field with an embedded 16px Lucide `Search` icon on the left (`#94A3B8`) and inline keyboard shortcut indicator (e.g., `⌘K`) on the right using a `code-compact` token badge.

### Metric Cards
- **Structure:** `#FFFFFF` fill, 1px solid `#E2E8F0` border, `6px` radius, padding `12px 16px`.
- **Content Flow:** Small upper label (`label-caption`, `#64748B`), large quantitative stat (`metric-display`, `#0F172A`, `tabular-nums`), followed by an inline trend chip (`+2.4% vs v1.2`) with muted semantic coloring.

### Requirement Diff & Code Blocks
- **Canvas:** Subdued background `#F1F5F9`, 1px solid `#E2E8F0` border, radius `4px`.
- **Inline Diffs:** Additions use background `#DCFCE7` with text `#15803D`. Removals/Ambiguities use background `#FEE2E2` with text `#B91C1C`. No colored glow; pure inline text highlighting.

### Icons
- **System:** Outline style (Lucide-based) set at a fixed `16px` by `16px` for inline actions/table rows, and `18px` by `18px` for primary navigation.
- **Stroke Width:** Unified at `1.5px` to balance with `Inter` 400/500 text weights.