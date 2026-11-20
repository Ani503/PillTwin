---
name: SamaSalt Design System
colors:
  surface: '#fbf9f6'
  surface-dim: '#dbdad7'
  surface-bright: '#fbf9f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f0'
  surface-container: '#efeeeb'
  surface-container-high: '#eae8e5'
  surface-container-highest: '#e4e2df'
  on-surface: '#1b1c1a'
  on-surface-variant: '#3e4947'
  inverse-surface: '#30312f'
  inverse-on-surface: '#f2f0ed'
  outline: '#6e7977'
  outline-variant: '#bdc9c6'
  surface-tint: '#006a63'
  primary: '#005c55'
  on-primary: '#ffffff'
  primary-container: '#0f766e'
  on-primary-container: '#a3faef'
  inverse-primary: '#80d5cb'
  secondary: '#99462b'
  on-secondary: '#ffffff'
  secondary-container: '#fe9574'
  on-secondary-container: '#762c13'
  tertiary: '#005f29'
  on-tertiary: '#ffffff'
  tertiary-container: '#087a38'
  on-tertiary-container: '#a3ffb2'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#9cf2e8'
  primary-fixed-dim: '#80d5cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#00504a'
  secondary-fixed: '#ffdbd0'
  secondary-fixed-dim: '#ffb59e'
  on-secondary-fixed: '#3a0a00'
  on-secondary-fixed-variant: '#7a2f16'
  tertiary-fixed: '#95f8a7'
  tertiary-fixed-dim: '#79db8d'
  on-tertiary-fixed: '#00210a'
  on-tertiary-fixed-variant: '#005323'
  background: '#fbf9f6'
  on-background: '#1b1c1a'
  surface-variant: '#e4e2df'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 34px
    fontWeight: '700'
    lineHeight: 42px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  title-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg-bold:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

The design system serves as an empowering, transparent public health utility engineered specifically for Indian users across diverse socioeconomic backgrounds, languages, and literacy levels. The ethos centers on parity, clarity, and uncompromising dignity: essential medicine is not a luxury, and deciphering active salts versus branded markups must be instantaneous and unambiguous.

The aesthetic fuses utilitarian clarity with civic warmth. By rejecting manipulative conversion patterns, aggressive clinical whites, and anxiety-inducing medical palettes, the interface establishes an environment of trusted public infrastructure. 

Key principles:
- **Radical Equivalence:** Every visual element reinforces that identical active ingredients carry identical efficacy regardless of packaging or brand fame.
- **Calm Reassurance over Alarmism:** Negative states, discrepancies, or missing alternatives must never present in punitive or alarming reds. Ambiguity is communicated with grounded, non-judgmental neutrality.
- **Cognitive Economy:** High visual affordance, generous touch targets, flat architectural borders, and immediate status recognition minimize cognitive load for first-time digital users and elders.

## Colors

The palette is anchored by deep therapeutic teal `#0F766E`, projecting institutional stability and medical precision without sterile coldness. The canvas avoids clinical starkness by using `#FAF8F5`, a warm organic off-white that improves outdoor readability in intense sunlight and eases screen fatigue.

Cards and surface elevations sit on crisp `#FFFFFF`, bounded by `#E2DED9` structural outlines. The coral accent `#F28B6B` is reserved exclusively for high-leverage contextual anchors (such as price delta highlights or key educational pills) and must never be applied to generic decorative details or standard interactive surfaces.

### Text Contrast
- High-emphasis text: `#1A1A1A` (near-black, exceeding AAA contrast against canvas and cards).
- Medium-emphasis text: `#5A5A5A` (balanced for secondary attributes, dosage subtitles, and metadata).
- Minimum accessible contrast rule: No informational text may register lower than 4.5:1 against its immediate backing container.

### Status Match System
Status indicators avoid red entirely to eliminate medical panic. Each state couples a dedicated border, container wash, foreground glyph, and label:

- **Exact Match:**
  - Foreground / Text: `#15803D`
  - Background Tint: `#DCFCE7`
  - Stroke: `#86EFAC`
  - Iconography: Bold Checkmark
- **Not Sure / Variant Salt:**
  - Foreground / Text: `#B45309`
  - Background Tint: `#FEF3C7`
  - Stroke: `#FDE68A`
  - Iconography: Rounded Question Mark
- **No Exact Match:**
  - Foreground / Text: `#475569`
  - Background Tint: `#F1F5F9`
  - Stroke: `#CBD5E1`
  - Iconography: Solid Minus / En-dash
- **Not Supported / Informational:**
  - Foreground / Text: `#64748B`
  - Background Tint: `#F8FAFC`
  - Stroke: `#E2E8F0`
  - Iconography: Filled Info Circle

## Typography

The design system uses Inter, supporting Devanagari (Hindi) and Bengali script extensions with native vertical metric alignment. 

### Typographic Rules
- **Three-Size Ceiling:** Any single screen template must restrict itself to a maximum of 3 distinct type sizes (for example: `headline-lg` 32px, `title-md` 20px, and `body-lg` 16px). Secondary hierarchy must be generated through font weight transitions (`400` regular to `600` semibold) and tone shift (`#1A1A1A` to `#5A5A5A`), not arbitrary point variations.
- **Strict Minimum Scale:** Type sizes below 14px are strictly prohibited anywhere across the system. Legal disclaimers, metadata stamps, and supplementary microcopy remain firmly set at 14px.
- **No All-Caps Badges:** All uppercase transforms are banned. Case transformations introduce significant cognitive delays in bilingual Indian script rendering and hinder rapid text recognition for emerging literacies. Sentence case is universally mandated.
- **Multilingual Density Management:** When rendering Hindi or Bengali, line-heights automatically increase by 10% to prevent conjunct clipping and diacritic overlap.

## Layout & Spacing

The layout is built for a 390px base portrait viewport with a strict edge-to-edge content container bounded by a 16px (`1rem`) outer margin.

### Structural Rhythm
- All screen layouts conform to a 4-column fluid mobile grid with 16px gutters and 16px outer boundary padding.
- Spacing follows an 8px base rhythm. Element padding internally uses 12px (`space-sm`) and 16px (`space-md`). Vertical flow sequences between decoupled cards use 16px (`space-md`), while semantic section divisions use 24px (`space-lg`) to 32px (`space-xl`).
- Structural cards span all 4 grid columns. Side-by-side medicine comparison matrices bifurcate equally into two 2-column cells separated by a 12px structural seam.

### Touch Ergonomics
- Interactive elements possess a hard minimum touch surface of 48px × 48px, with standard primary trigger heights fixed at 56px.
- Key navigation buttons and salt-selection CTAs are anchored within thumb-reach zones along the bottom 30% of the viewport.

## Elevation & Depth

This design system deliberately eschews dimensional illusions, multi-stop gradients, skeuomorphic shading, and frosted glass treatments in favor of crisp architectural planar boundaries.

### Border-Defined Architecture
- Depth and component isolation are accomplished entirely through high-precision 1px outlines (`#E2DED9`) mapped directly over contrasting white `#FFFFFF` cards against the `#FAF8F5` background.
- Heavy drop shadows are omitted. Ambient drop shadows are permitted only on sticky bottom CTA bars to clearly indicate separation from scrolling surface content below, configured as: `0px 4px 20px rgba(26, 26, 26, 0.06)`.
- Active, pressed, or focused states never drop downward shadows; they translate feedback solely through outline color shifts to `#0F766E` and subtle tint adjustments.

## Shapes

A uniform 16px corner radius is applied to all surface components, creating a cohesive visual cadence across cards, containers, input regions, and modal sheets.

### Corner Architecture
- Standard surfaces (Medicine Cards, Comparison Containers, Input Boxes): 16px border-radius.
- Primary and secondary buttons: 16px border-radius, maintaining harmony with surrounding cards.
- Status badges and contextual tags: 16px or full-pill configuration to convey self-contained, atomic information.
- Modal bottom sheets: 16px top-left and top-right radii; zero bottom radii.

## Components

### Buttons
- **Primary Button:** Fixed 56px height, full width or minimum 180px inline. Solid `#0F766E` background with `#FFFFFF` text in 16px Semibold. Roundedness set to 16px. Active state transitions to `#115E59`.
- **Secondary Button:** Fixed 56px height. Pure `#FFFFFF` background with 1px `#E2DED9` solid border. Text set in `#1A1A1A` 16px Semibold.
- **Tertiary Utility Action:** Minimum 48px height, transparent background, `#0F766E` 16px Semibold text, underlined or bracketed with a 2px icon.

### Status Match Badges
- Structural attributes: 32px height, 12px horizontal padding, 1px perimeter border, 16px radius.
- Icons are drawn with uniform 2px stroke weight, sized at 16px × 16px, vertically aligned with 14px Semibold text.
- Text uses natural sentence case (e.g., "Exact match", "Alternative salt", "Not confirmed"). All-caps text is banned.

### Medicine Comparison Cards
- Base surface: `#FFFFFF`, 16px border-radius, 1px `#E2DED9` perimeter border, 16px interior padding.
- Structure: Split comparison header presenting the prescribed brand alongside the verified generic alternative. 
- Price Display: Current branded retail price in `#5A5A5A` with strike-through versus SamaSalt fair price in `#0F766E` 20px Bold. The price delta savings tag uses `#F28B6B` text over a 10% opacity coral fill.

### Input Fields
- Fixed 56px container height with 16px horizontal internal padding.
- Border: 1px `#E2DED9` default; transitions to 2px `#0F766E` upon active keyboard focus.
- Background: `#FFFFFF`.
- Typography: 16px `#1A1A1A` input text with `#5A5A5A` placeholder. Clear affordances with 2px line search icons and 48px tap-clearing touch targets.

### Checkboxes & Radio Switches
- Minimum touch target: 48px × 48px bounding container; physical glyph footprint: 24px × 24px.
- Inactive: 2px solid `#E2DED9` border over `#FFFFFF` backing.
- Selected: `#0F766E` solid fill with `#FFFFFF` 2px bold checkmark or inner core.

### Iconography
- Flat 2px uniform monoline strokes with rounded caps and joins.
- Icon frames default to 24px × 24px with a 48px accessible touch envelope when acting as triggers.
- Icons must pair with descriptive text labels whenever introducing diagnostic states, active chemical compositions, or dosage instructions.