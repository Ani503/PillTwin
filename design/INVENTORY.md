# PillTwin Design Inventory & Gap Analysis

**Generated:** 2026-11-19  
**Source Directory:** `design/_unzipped`  
**Tokens File:** `design/tokens.json`  

## 1. Exported Screens & Assets Found

| Folder / Screen Name | HTML Template | PNG Preview | Design System Doc |
| :--- | :--- | :--- | :--- |
| `camera_scan` | Yes (`code.html`) | Yes (`screen.png`) | No |
| `home` | Yes (`code.html`) | Yes (`screen.png`) | No |
| `language_choice` | Yes (`code.html`) | Yes (`screen.png`) | No |
| `review_detected_names` | Yes (`code.html`) | Yes (`screen.png`) | No |
| `samasalt_design_system` | No | No | Yes (`DESIGN.md`) |

## 2. Complete User Flow Mapping & Coverage Gap

| Flow Step | Stitch Screen Found | Status in Export | Notes & Implementation Requirements |
| :--- | :--- | :--- | :--- |
| **Language** | `language_choice` | **Present** | Full screen language selection (English, Hindi, Bengali) with radio indicators |
| **Home** | `home` | **Present** | Header with wordmark, search drawer trigger, scan CTA, info cards, bottom navigation |
| **How it works** | `None` | **Missing** | Needs implementation (accessible educational modal/page on salt matching and savings) |
| **Permission denied** | `None` | **Missing** | Needs implementation (camera permission fallback instructing user to allow camera or upload photo) |
| **Scan** | `camera_scan` | **Present** | Camera viewfinder with quality chips (light, sharpness, glare), bounding box, shutter, upload photo fallback |
| **Type a name** | `home & review_detected_names` | **Partially Present** | Integrated as collapsible tray on Home and bottom sheet on Review |
| **Review names** | `review_detected_names` | **Present** | Detected medicine list with Edit, Remove, Type a name, and Find Generics CTA |
| **Matching** | `None` | **Missing** | Needs implementation (animated loading state while exact match engine runs) |
| **Result list** | `None` | **Missing** | Needs implementation (Cards for Exact match [green], Not sure [amber], No match [slate], Unsupported [slate]) |
| **Medicine detail** | `None` | **Missing** | Needs implementation (per-unit price math, dosage form comparison, caution drug banner) |
| **Total** | `None` | **Missing** | Needs implementation (prescription total cost comparison and per-month savings calculation) |
| **Where to buy** | `None` | **Missing** | Needs implementation (link-out to official PMBI Kendra locator at pmbi.co.in) |
| **Learn** | `None` | **Missing** | Needs implementation (tab in nav: what is a salt, bioequivalence, PMBJP quality standards) |
| **About** | `None` | **Missing** | Needs implementation (tab in nav: project background, metrics from metrics.json, data date, disclaimer) |
| **Privacy** | `None` | **Missing** | Needs implementation (no photos stored, no accounts, no tracking, in-memory processing only) |
| **Help** | `None` | **Missing** | Needs implementation (frequently asked questions and user guidance) |
| **Settings** | `None` | **Missing** | Needs implementation (language switcher, large text mode toggle, dark theme toggle) |
| **Error** | `None` | **Missing** | Needs implementation (general error handling screen for network/server failure) |
| **Offline** | `None` | **Missing** | Needs implementation (PWA offline fallback banner and cache behavior) |

## 3. Design Tokens Comparison & Specification Compliance

| Token Attribute | Project Spec | Stitch Exported Value | Status / Action |
| :--- | :--- | :--- | :--- |
| **Primary Color** | `#0F766E` (Teal) | `#005C55` (with `#0F766E` as container) | Align to canonical `#0F766E` |
| **Canvas / Background** | `#FAF8F5` (Warm off-white) | `#FBF9F6` | Correct to `#FAF8F5` |
| **Accent Color** | `#F28B6B` (Coral) | `#99462B` / `#FE9574` | Standardize to `#F28B6B` |
| **Typography** | Inter (14px to 34px) | Inter (includes 11px, 12px) | Remove sub-14px font sizes |
| **Corner Radius** | `16px` uniform | Mixed (`4px`, `8px`, `12px`, `16px`, `24px`) | Standardize all surfaces to `16px` |
| **Borders & Dividers** | `1px solid #E2DED9` | `1px solid #6E7977` / `#BDC9C6` | Use `#E2DED9` border architecture |
| **Drop Shadows** | **None** | `shadow-sm`, `shadow-md`, `shadow-xl`, ambient bar shadow | **Strip all shadows** |
| **Gradients** | **None** | Multiple linear gradients in camera view | **Replace with flat colors** |
| **Error / Warning Colors** | **No red** | `#BA1A1A`, `#FFDAD6` in design system | **Remove red tokens**; status only |

## 4. Flagged Problems in Stitch Exports (Items A-H)

### A. Photos, Faces, or Readable Real Brand Text (2 items flagged)
- **`camera_scan/code.html`**: Viewfinder includes background medicine blister foil strip imagery / data-alt mockup description
- **`review_detected_names/code.html`**: Mockup contains hardcoded medicine names 'Brandex 500 tablet' and 'Cardiofix 5'

### B. Hardcoded Prices, Savings, Percentages, and Metrics (2 items flagged)
- **`home/code.html`**: Hardcoded price/percentage/strength: '50% to 90%'
- **`review_detected_names/code.html`**: Hardcoded price/percentage/strength: '500mg'

### C. False, Marketing, or Legally Risky Claims (10 items flagged)
- **`language_choice/code.html`**: Matched forbidden claim pattern: 'verified'
- **`home/code.html`**: Matched forbidden claim pattern: '50% to 90%'
- **`home/code.html`**: Matched forbidden claim pattern: 'certified manufacturers'
- **`home/code.html`**: Matched forbidden claim pattern: 'certified'
- **`home/code.html`**: Matched forbidden claim pattern: 'verified'
- **`samasalt_design_system/DESIGN.md`**: Matched forbidden claim pattern: 'public health utility'
- **`samasalt_design_system/DESIGN.md`**: Matched forbidden claim pattern: 'verified'
- **`camera_scan/code.html`**: Matched forbidden claim pattern: 'Data Dignity'
- **`camera_scan/code.html`**: Matched forbidden claim pattern: 'verified'
- **`review_detected_names/code.html`**: Matched forbidden claim pattern: 'verified'

### D. Broken Images, Avatars, and Legacy 'SamaSalt' References (1 items flagged)
- **`samasalt_design_system/DESIGN.md`**: Found legacy brand name 'SamaSalt'

### E. Profile Avatars and Duplicate Language Switchers (1 items flagged)
- **`language_choice/code.html`**: Duplicate language switcher present (header button + banner pill group)

### F. Red Used for Warnings or Error Palettes (5 items flagged)
- **`language_choice/code.html`**: Red styling detected: #93000a, #ba1a1a, #ffdad6
- **`home/code.html`**: Red styling detected: #93000a, #ba1a1a, #ffdad6
- **`samasalt_design_system/DESIGN.md`**: Red styling detected: #93000a, #ba1a1a, #ffdad6
- **`camera_scan/code.html`**: Red styling detected: #93000a, #ba1a1a, #ffdad6
- **`review_detected_names/code.html`**: Red styling detected: #93000a, #ba1a1a, #ffdad6

### G. External Resources (CDNs, Google Fonts, Scripts) (24 items flagged)
- **`language_choice/code.html`**: Remote CDN/Font resource: 'https://fonts.gstatic.com'
- **`language_choice/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap'
- **`language_choice/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200'
- **`language_choice/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap'
- **`language_choice/code.html`**: Remote CDN/Font resource: 'https://cdn.tailwindcss.com'
- **`language_choice/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com'
- **`home/code.html`**: Remote CDN/Font resource: 'https://fonts.gstatic.com'
- **`home/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap'
- **`home/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200'
- **`home/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap'
- **`home/code.html`**: Remote CDN/Font resource: 'https://cdn.tailwindcss.com'
- **`home/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com'
- **`camera_scan/code.html`**: Remote CDN/Font resource: 'https://fonts.gstatic.com'
- **`camera_scan/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap'
- **`camera_scan/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200'
- **`camera_scan/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap'
- **`camera_scan/code.html`**: Remote CDN/Font resource: 'https://cdn.tailwindcss.com'
- **`camera_scan/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com'
- **`review_detected_names/code.html`**: Remote CDN/Font resource: 'https://fonts.gstatic.com'
- **`review_detected_names/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap'
- **`review_detected_names/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200'
- **`review_detected_names/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap'
- **`review_detected_names/code.html`**: Remote CDN/Font resource: 'https://cdn.tailwindcss.com'
- **`review_detected_names/code.html`**: Remote CDN/Font resource: 'https://fonts.googleapis.com'

### H. Typography Scaling Under Accessible 14px Floor (4 items flagged)
- **`language_choice/code.html`**: Text scale below 14px: text-xs
- **`home/code.html`**: Text scale below 14px: text-xs
- **`camera_scan/code.html`**: Text scale below 14px: text-xs
- **`review_detected_names/code.html`**: Text scale below 14px: text-xs

