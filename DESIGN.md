---
name: Kanban Studio
description: A calm light kanban board with one blue accent and a first-class AI assistant panel.
colors:
  ground: "#f6f7f9"
  well: "#eceef2"
  surface: "#ffffff"
  line: "#dde1e8"
  line-strong: "#c3cad6"
  ink: "#172033"
  muted: "#566073"
  accent: "#1f5fe0"
  accent-strong: "#1a4fc0"
  accent-soft: "#e8effd"
  danger: "#b42a21"
  danger-soft: "#fdecea"
  dot-backlog: "#8792a5"
  dot-discovery: "#7c5cdb"
  dot-progress: "#1f5fe0"
  dot-review: "#d98a00"
  dot-done: "#1f9d6b"
typography:
  title-lg:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.33
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  body-strong:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
  secondary:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: "20px"
  label:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.5
  caption:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.33
    fontFeature: "tnum"
rounded:
  md: "6px"
  lg: "8px"
  xl: "12px"
  bubble: "16px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
    typography: "{typography.label}"
    height: "32px"
    padding: "0 12px"
  button-primary-hover:
    backgroundColor: "{colors.accent-strong}"
  button-primary-lg:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    typography: "{typography.body}"
    height: "40px"
  button-outline:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    typography: "{typography.label}"
    height: "32px"
    padding: "0 12px"
  button-ghost:
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
    typography: "{typography.label}"
    height: "32px"
    padding: "0 12px"
  button-ghost-hover:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
  button-delete-hover:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "12px"
  column-well:
    backgroundColor: "{colors.well}"
    rounded: "{rounded.xl}"
    padding: "8px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.xl}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    typography: "{typography.body}"
    padding: "6px 10px"
  input-lg:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    typography: "{typography.body}"
    height: "40px"
    padding: "0 12px"
  count-badge:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    rounded: "{rounded.full}"
    typography: "{typography.caption}"
    padding: "2px 8px"
  message-user:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.bubble}"
    typography: "{typography.body}"
    padding: "8px 12px"
  message-assistant:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    rounded: "{rounded.bubble}"
    typography: "{typography.body}"
    padding: "8px 12px"
  top-bar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    height: "56px"
---

# Design System: Kanban Studio

## Overview

**Creative North Star: "The Quiet Workbench"**

This is the category standard played straight: a calm, cool-tinted light board where the work is the only loud thing. Neutrals do almost all of the job; a single blue marks what is actionable (primary buttons, focus, the user's own chat bubbles) and five muted status dots are the only other colour on screen. Cards are small white sheets on slightly darker wells, separated by 1px lines and a faint shadow, so the board stays scannable when it fills.

The assistant panel is a first-class peer of the board, not a floating widget: docked, sticky, same surface vocabulary, with an explicit thinking state for slow model replies. Density is compact (14px base, 13px secondary, 32px controls) and motion is nearly absent. The system confirmed-rejects the soft-SaaS template: blurred blobs, a marketing header, tracked uppercase labels, giant radii.

**Key Characteristics:**
- Light only (`color-scheme: light`); no dark theme exists.
- One accent blue; status colour is limited to a 8px dot per column.
- Tonal layering (ground, well, white surface) plus 1px borders; shadows are soft and few.
- Geist throughout, tabular numerals for counts.
- Drawn SVG icons at 14px, stroked with currentColor.

## Colors

A cool-tinted neutral field with a single blue and five desaturated status hues.

### Primary
- **Signal Blue** (`accent`): primary buttons, the 2px focus ring, input focus border, caret, the user's chat bubbles, the spinner, the assistant header icon, and the drop-target inset ring on columns.
- **Signal Blue Pressed** (`accent-strong`): hover state of every blue button only.
- **Blue Mist** (`accent-soft`): the assistant header icon chip and text selection background.

### Neutral
- **Cool Ground** (`ground`): page background; also the hover fill of the outline Log out button and the demo-credentials note.
- **Column Well** (`well`): column backgrounds, assistant message bubbles, ghost-button hover.
- **Paper White** (`surface`): top bar, cards, panels, inputs, login card.
- **Hairline** (`line`): default 1px borders on cards, panels, inputs, top bar.
- **Hairline Strong** (`line-strong`): hovered borders, dashed empty-column and dragging outlines, scrollbar thumbs.
- **Ink Navy** (`ink`): headings, card titles, body text on white.
- **Slate Muted** (`muted`): card details, counts, helper text, inactive controls.

### Status and feedback
- **Danger Red** (`danger`) with **Danger Tint** (`danger-soft`): card delete hover, inline errors, error toast.
- **Status dots** (`dot-backlog` slate, `dot-discovery` violet, `dot-progress` blue, `dot-review` amber, `dot-done` green): assigned to columns by index, cycling; never used for fills, text, or borders.

### Named Rules
**The One Blue Rule.** Blue means "you can act here" or "this is you". It is not decoration, not a section tint, not a status colour.
**The Dot-Only Status Rule.** The five status hues appear only as the 8px dot beside a column title.

## Typography

**Display Font:** none; no display face exists.
**Body Font:** Geist (via next/font, `--font-geist`) with Segoe UI, system-ui, sans-serif fallback.

**Character:** One neutral, precise sans in a small range of weights (400, 500, 600). Hierarchy comes from size, weight and ink-versus-muted colour, not from case or tracking tricks.

### Hierarchy
- **Title Large** (600, 24px, tight tracking): login heading only.
- **Title** (600, 15px, tight tracking): "Kanban Studio" wordmark in top bar and login.
- **Body Strong** (600, 14px): column titles, panel heading. Card titles are 14px at 500, leading 20px.
- **Body** (400, 14px, 1.5): inputs, chat messages, default text.
- **Secondary** (400, 13px, 20px leading): card details, helper and empty-state text.
- **Label** (500, 13px): buttons, form labels, username.
- **Caption** (500, 12px, tabular numerals): column count badges, composer hint, thinking text.

### Named Rules
**The Two-Greys Rule.** Text is either ink or muted. Do not introduce a third text grey; the one existing hardcoded placeholder grey is drift (see below).

## Layout

App shell: a 56px sticky top bar (white, bottom hairline, wordmark left, username and Log out right) over a main area padded 16px (24px at 2xl). With the assistant present, main is a two-track grid: board on the left, assistant panel 300px at lg and 340px at 2xl, sticky below the bar (top 4.5rem). Below lg the assistant stacks under the board at a fixed 34rem height.

The board is five columns: horizontal scroll with 16rem minimum column width below xl, an equal five-column grid at xl and above. Gap between columns is 12px; inside a well, padding is 8px and cards stack with 8px gaps. Card padding is 12px. The rhythm is a 4px-based scale (4, 8, 12, 16, 24) with 32px controls and 40px on the login form. The login is a single 400px-max card centred on the ground.

## Elevation & Depth

Hybrid: tonal layering carries hierarchy (ground, well, white), 1px borders define edges, and shadows are soft and ink-tinted (rgba of the ink colour), never coloured or hard-offset.

### Shadow Vocabulary
- **Card** (`--elev-card`: `0 1px 2px rgba(23,32,51,.08), 0 1px 1px rgba(23,32,51,.04)`): cards at rest and the open new-card form.
- **Lift** (`--elev-lift`: `0 12px 28px rgba(23,32,51,.16), 0 3px 8px rgba(23,32,51,.1)`): things above the board: the error toast.
- **Panel** (`--elev-panel`: `0 1px 3px rgba(23,32,51,.08), 0 8px 24px rgba(23,32,51,.05)`): assistant panel and login card.

### Named Rules
**The Quiet Shadow Rule.** Shadows are soft and ink-tinted, and a surface gets the one that matches its role. A dragged-from card drops its shadow entirely.

## Shapes

Gentle, consistent corners: 6px (rounded-md) for buttons, inputs and small controls; 8px (rounded-lg) for cards, the login inputs and primary login button; 12px (rounded-xl) for column wells and panels; 16px for chat bubbles with one 6px tail corner on the speaker's side; full pill for count badges and status dots. Borders are always 1px; the only dashed borders are the empty-column drop hint and the card being dragged. Icons are drawn SVG at 14px, no glyph or emoji icons.

## Components

### Buttons
- **Shape:** 6px corners, 32px high, 13px/500 label (login submit: 8px, 40px, 14px).
- **Primary:** Signal Blue fill, white text, 12px side padding; optional 14px leading icon (Send).
- **Hover / Focus:** fill shifts to the pressed blue; focus ring is 2px accent with 2px offset (0 offset on text fields). Disabled drops to 50% opacity.
- **Outline:** white, 1px hairline, ink text (Log out); hover darkens border and fills ground.
- **Ghost:** muted text, no fill; hover fills well and turns text ink (Cancel, "Add a card").
- **Delete:** 24px square, muted x icon; hover turns danger tint with danger text.

### Cards / Containers
- **Corner Style:** 8px. **Background:** white on a well. **Border:** 1px hairline, hover to strong. **Shadow:** Card. **Padding:** 12px.
- Title 14px/500 ink, details 13px muted clamped to 4 lines. Cursor is grab. While dragging, the source becomes a dashed, 50%-opacity, shadowless placeholder.

### Column well
- 12px radius, `well` fill, 8px padding. Header: status dot, editable title input (transparent, white tint on hover and focus), tabular count pill. Empty state is a dashed 96px-min box reading "Drop a card here". An active drop target gets a 2px accent inset ring.

### Inputs / Fields
- White, 1px hairline, 6px radius, 14px text; hover strengthens border, focus swaps border to accent plus the focus ring. The chat composer wraps textarea and Send in one bordered shell whose border turns accent on focus-within.

### Assistant panel
- White 12px panel with Panel shadow: header (blue-mist icon chip, 14px/600 title), scrolling message list, inline danger error line, composer. User bubbles are blue/white right-aligned (max 85%); assistant bubbles are well/ink left-aligned (max 90%). The thinking state is a well bubble with "Working on your board" and three pulsing dots (role=status). Motion: a single 220ms ease-out message entrance and the 1.2s thinking-dot pulse; both are disabled under prefers-reduced-motion, which also collapses transitions.

### Navigation
- Top bar only: 56px, white, hairline bottom, sticky at z-20. Username hides below sm.

## Do's and Don'ts

### Do:
- **Do** use `ground`, `well`, `surface` as the only background tiers, and 1px `line` borders for edges.
- **Do** reserve Signal Blue for primary actions, focus, and the user's own chat bubbles.
- **Do** keep status colour to the 8px column dot.
- **Do** use 14px body, 13px secondary, 32px controls, and tabular numerals for counts.
- **Do** pair every new interactive element with the 2px accent focus-visible ring.
- **Do** keep motion to the existing entrance and thinking pulse, and respect prefers-reduced-motion.
- **Do** draw new icons as 14px currentColor SVGs in the existing set.

### Don't:
- **Don't** add a dark theme, gradients, blurred blobs, or a marketing header.
- **Don't** use radii above 12px on containers (16px is bubbles only).
- **Don't** use coloured or hard-offset shadows; use the three elevation tokens.
- **Don't** introduce a second accent or fill surfaces with status colours.
- **Don't** use tracked uppercase labels; hierarchy is by size, weight and ink versus muted.
- **Don't** use emoji or glyph characters as icons.
