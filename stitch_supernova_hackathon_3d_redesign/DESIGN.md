---
name: Obsidian Quantum Cyber-Horror
colors:
  surface: '#161214'
  surface-dim: '#161214'
  surface-bright: '#3d383a'
  surface-container-lowest: '#110d0f'
  surface-container-low: '#1f1a1d'
  surface-container: '#231e21'
  surface-container-high: '#2e292b'
  surface-container-highest: '#393336'
  on-surface: '#eae0e3'
  on-surface-variant: '#e8bcba'
  inverse-surface: '#eae0e3'
  inverse-on-surface: '#342f31'
  outline: '#ae8785'
  outline-variant: '#5e3f3e'
  surface-tint: '#ffb3b0'
  primary: '#ffb3b0'
  on-primary: '#680010'
  primary-container: '#ff5359'
  on-primary-container: '#5b000d'
  inverse-primary: '#bf0026'
  secondary: '#ffb3b1'
  on-secondary: '#670212'
  secondary-container: '#8b2028'
  on-secondary-container: '#ff9e9c'
  tertiary: '#ffb2bd'
  on-tertiary: '#670024'
  tertiary-container: '#ec627f'
  on-tertiary-container: '#5a001f'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b0'
  on-primary-fixed: '#410006'
  on-primary-fixed-variant: '#93001b'
  secondary-fixed: '#ffdad8'
  secondary-fixed-dim: '#ffb3b1'
  on-secondary-fixed: '#410007'
  on-secondary-fixed-variant: '#871e26'
  tertiary-fixed: '#ffd9dd'
  tertiary-fixed-dim: '#ffb2bd'
  on-tertiary-fixed: '#400013'
  on-tertiary-fixed-variant: '#8a1638'
  background: '#161214'
  on-background: '#eae0e3'
  surface-variant: '#393336'
typography:
  display-hero:
    fontFamily: Syne
    fontSize: 4rem
    fontWeight: '800'
    lineHeight: 4.25rem
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Syne
    fontSize: 2.5rem
    fontWeight: '800'
    lineHeight: 2.75rem
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Syne
    fontSize: 2.5rem
    fontWeight: '700'
    lineHeight: 3rem
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Syne
    fontSize: 1.75rem
    fontWeight: '700'
    lineHeight: 2.25rem
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Syne
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Syne
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: 0em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 1.125rem
    fontWeight: '400'
    lineHeight: 1.75rem
    letterSpacing: -0.01em
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: 0em
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
    letterSpacing: 0.01em
  label-code:
    fontFamily: Space Mono
    fontSize: 0.8125rem
    fontWeight: '700'
    lineHeight: 1.25rem
    letterSpacing: 0.08em
  label-telemetry:
    fontFamily: Space Mono
    fontSize: 0.6875rem
    fontWeight: '400'
    lineHeight: 1rem
    letterSpacing: 0.12em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  gutter-lg: 2rem
  margin: 1.5rem
  margin-sm: 1rem
  margin-lg: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
  space-2xl: 4rem
---

## Brand & Style

This design system defines an elite, speculative collegiate hackathon interface operating at the convergence of quantum cryptography, deep void aesthetics, and cyber-horror. The UI evokes the claustrophobic dread of a deep-space research vessel whose core containment protocols have fractured, paired with the surgical precision of high-velocity terminal infrastructure.

### Aesthetic Foundation
- **Obsidian Monoliths & Smoked Glass**: Layered near-black surfaces (`#09070A`, `#10090E`, `#170B10`) behaving like treated titanium and radiation-shielded glass.
- **Controlled Crimson Luminescence**: Pinpoint photon bleeds and high-intensity lasers (`#FF263F`, `#FF718E`) contrasting against absolute carbon darkness. Accents are weaponized, not ornamental.
- **Cyber-Horror Sci-Fi HUD**: Tactical reticles, telemetry labels, micro-registration marks, telemetry readouts, and sharp chamfered or tight-radius perimeter containment frames.
- **Authoritative Tension**: Contrast between editorial, cinematic typographic gravitas and cold, terminal-driven telemetry.

## Colors

The palette establishes an aggressive dark-field spectrum engineered for high-stress collegiate competition and immersive technical storytelling.

### Core Swatches
- **Void Obsidian (`#09070A`)**: Ground-floor canvas and unlit viewport backdrop.
- **Deep Burgundy Surface (`#170B10`)**: Smoked glass container backings, HUD modular decks, and elevated panels.
- **Secondary Surface (`#10090E`)**: Recessed modules, code mirrors, inputs, and muted drawer panels.
- **Electric Crimson (`#FF263F`)**: Primary signal vector. Used for primary CTAs, critical warning thresholds, terminal status pings, and active telemetry states.
- **Dark Burgundy (`#710B18`)**: Structural grounding tone; used for pressed states, containment fills, and perimeter frame anchors.
- **Supporting Border (`#542032`)**: The structural wireframe; delivers crisp demarcation of panels without blowing out canvas contrast.
- **Highlight Red (`#FF718E`)**: Precision focal points, rim light gleams, focus rings, and high-frequency data spikes.
- **Main Text (`#EEE4E7`)**: Bone-white readability grade; high legibility across dark surfaces.
- **Secondary Muted Text (`#AD969D`)**: Desaturated ash rose for structural metadata, secondary timestamps, and HUD legends.

### Application Rules
- Never use pure black (`#000000`) for surfaces; retain the bio-chemical obsidian warmth of `#09070A`.
- Reserve `#FF263F` for dynamic actionable points and critical security breaches; UI saturation fatigue occurs if background panels leverage it as solid fills.
- Borders must sit between `0.5px` and `1px` solid `#542032`, simulating machined chassis seams.

## Typography

The typographic hierarchy orchestrates a high-contrast clash between **Syne** (avant-garde, visceral, brutalist display), **Plus Jakarta Sans** (pure optical clarity for long-form mission briefs and rules), and **Space Mono** (cold, deterministic command telemetry).

### Scale & Hierarchy Rules
- **Display & Headlines (`Syne`)**: Render in `#EEE4E7`. Use uppercase transforms for event tracking titles and category markers (`HACK_TRACK_01 // QUANTUM ENCRYPTION`).
- **Body (`Plus Jakarta Sans`)**: Neutralized legibility. Primary prose uses `#EEE4E7`; footnotes, contextual prompts, and secondary information rely on `#AD969D`.
- **System Telemetry & Metadata (`Space Mono`)**: Always rendered with uppercase transforms, wide tracking (`letter-spacing: 0.08em` to `0.12em`), and prefixed markers (e.g., `[LOC://CORE_LAB]`, `SEC_STATUS: HAZARD`).

## Layout & Spacing

The structural rhythm reflects high-density technical control panels: precision spacing, balanced margins, and uninterrupted telemetry lines.

### Grid Architecture
- **Desktop (>= 1200px)**: 12-column layout, `3rem` canvas margin, `2rem` gutters. Content containers lock to a maximum width of `1360px`.
- **Tablet (768px - 1199px)**: 8-column layout, `1.5rem` canvas margin, `1.5rem` gutters. Sidebars collapse into docked overlays.
- **Mobile (< 768px)**: 4-column layout, `1rem` outer canvas margin, `1rem` gutters. Complex data grids reflow into vertically stacked telemetry cards.

### Micro-Spacing & Cadence
- Use `space-xs` (4px) and `space-sm` (8px) for internal module telemetry: pairing icons with labels, attaching code prefixes, and grouping badge items.
- Use `space-md` (16px) and `space-lg` (24px) for component padding inside cards, forms, and dialog panels.
- Use `space-xl` (40px) and `space-2xl` (64px) strictly for section separation and visual decompression zones.

## Elevation & Depth

Visual hierarchy uses physical material stratification rather than generic drop shadows. The illusion of a terminal visor backed by deep obsidian vacuum is achieved via backdrops, precise inner edges, and laser glow.

### Stratification Levels
1. **Canvas (Depth 0 - Ground Zero)**: Pure `#09070A`. Non-interactive baseline viewport.
2. **Decks & Smoked Panels (Depth 1)**: `#170B10` at 70% opacity with a `16px` backdrop-filter blur (`blur(16px)`). Bound by a 1px solid `#542032` border.
3. **Elevated HUD Modules & Modals (Depth 2)**: `#170B10` with a top-down interior rim light: `inset 0 1px 0 0 rgba(255, 113, 142, 0.25)` and a soft outward crimson falloff: `0 8px 32px -4px rgba(113, 11, 24, 0.45)`.
4. **Active Vector State / Critical Focal Point (Depth 3)**: High-luminance activation: `0 0 16px rgba(255, 38, 63, 0.45), 0 0 1px 1px #FF263F`.

### Edge Rim-Lighting
Every card or interactive deck leverages a subtle directional gradient border: running from `#FF718E` (top edge, 30% opacity) down to `#542032` (80% opacity) to `#170B10` (bottom edge, 100% opacity), mimicking an overhead console diode illuminating precision chassis seams.

## Shapes

The design uses a strict `0.25rem` (4px) core radius (`roundedness: 1`), conveying machined carbon composite and cold aerospace plating. 

### Geometric Rules
- **Standard UI Containers (Cards, Inputs, Buttons)**: Fixed `4px` corner radii. Pill or stadium shapes are strictly forbidden to prevent an uncharacteristic friendly or generic SaaS appearance.
- **Structural HUD Chamfers**: Where enhanced tactical geometry is required, elements may utilize a `4px` 45-degree corner cut (`clip-path: polygon(...)`) on opposing corners (top-right and bottom-left).
- **Framing Brackets**: High-priority modules may feature L-shaped outer corner markers (`border-top`, `border-left` spanning 8px x 8px) set in `#FF263F`.

## Components

### Buttons
- **Primary Cyber Button**: 
  - Background: `#FF263F`.
  - Text: `#09070A`, `Space Mono`, bold, all-caps, `0.08em` letter spacing.
  - Border: 1px solid `#FF718E`.
  - Hover: Background shifts to `#FF718E`; box-shadow triggers `0 0 20px rgba(255, 38, 63, 0.6)`.
  - Active: Scale transform `0.98`; background settles to `#710B18`, text shifts to `#EEE4E7`.
- **Secondary / HUD Ghost Button**: 
  - Background: `rgba(23, 11, 16, 0.6)`.
  - Text: `#EEE4E7`, `Space Mono`.
  - Border: 1px solid `#542032`.
  - Hover: Border switches to `#FF263F`, text gains subtle crimson text-shadow glow (`0 0 8px rgba(255, 38, 63, 0.5)`).

### Cards & Viewport Modules
- **Construction**: Smoked background `#170B10` with `backdrop-filter: blur(12px)`.
- **Border**: 1px solid `#542032`.
- **Header Accent**: Top edge features a 1px inner rim highlight (`rgba(255, 113, 142, 0.2)`).
- **Card Header**: Rendered with small metadata label prefix in `Space Mono` (e.g., `// MOD_04 // ANOMALY_DETECTION`) in `#AD969D`.

### Form Inputs & Terminal Fields
- **Container**: `#10090E` background, 1px solid `#542032`, `4px` border radius.
- **Text**: `#EEE4E7` in `Plus Jakarta Sans`, placeholder text in `#AD969D` at 50% opacity.
- **Focus State**: Border sharply transitions to `#FF263F` with an outer glow `0 0 0 1px #FF263F, 0 0 12px rgba(255, 38, 63, 0.25)`. Outline: none.

### Chips & Telemetry Badges
- **Form**: Compact height (24px), `4px` radius, typography `Space Mono` (`label-telemetry`).
- **Critical Status**: Background `rgba(255, 38, 63, 0.12)`, text `#FF718E`, border `1px solid rgba(255, 38, 63, 0.4)`. Contains a pulsing 4px circular LED indicator in `#FF263F`.
- **Muted Category**: Background `rgba(84, 32, 50, 0.2)`, text `#AD969D`, border `1px solid #542032`.

### Selection Controls (Checkboxes & Radios)
- **Base**: `16px` square or circle, background `#10090E`, border `1px solid #542032`.
- **Selected**: Background `#FF263F`, border `#FF718E`. Check glyph is sharp, high-contrast bone-white (`#09070A`) micro-mark.

### Bespoke Domain Components
- **Quantum State Indicator**: Real-time glitching readout ticker showing team compute allocation, styled with CSS scanlines (`repeating-linear-gradient`).
- **Telemetry Countdown Clock**: Split-flap/monospaced numbers in `Syne` and `Space Mono` displaying mission time until final quantum core submission lockout.
- **Countdown HUD Matrix**: Monospace coordinate system indicating server cluster health across hackathon tracks.