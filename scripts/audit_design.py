import os
import re
import json

def audit_designs():
    unzipped_dir = 'design/_unzipped'
    screens = []
    
    # Check all subdirectories
    for item in sorted(os.listdir(unzipped_dir)):
        item_path = os.path.join(unzipped_dir, item)
        if os.path.isdir(item_path):
            files = os.listdir(item_path)
            screens.append({
                'name': item,
                'path': item_path,
                'files': files,
                'has_html': 'code.html' in files,
                'has_png': 'screen.png' in files,
                'has_md': 'DESIGN.md' in files
            })

    # Flow mapping
    flow_steps = [
        ("Language", "language_choice", "Present", "Full screen language selection (English, Hindi, Bengali) with radio indicators"),
        ("Home", "home", "Present", "Header with wordmark, search drawer trigger, scan CTA, info cards, bottom navigation"),
        ("How it works", "None", "Missing", "Needs implementation (accessible educational modal/page on salt matching and savings)"),
        ("Permission denied", "None", "Missing", "Needs implementation (camera permission fallback instructing user to allow camera or upload photo)"),
        ("Scan", "camera_scan", "Present", "Camera viewfinder with quality chips (light, sharpness, glare), bounding box, shutter, upload photo fallback"),
        ("Type a name", "home & review_detected_names", "Partially Present", "Integrated as collapsible tray on Home and bottom sheet on Review"),
        ("Review names", "review_detected_names", "Present", "Detected medicine list with Edit, Remove, Type a name, and Find Generics CTA"),
        ("Matching", "None", "Missing", "Needs implementation (animated loading state while exact match engine runs)"),
        ("Result list", "None", "Missing", "Needs implementation (Cards for Exact match [green], Not sure [amber], No match [slate], Unsupported [slate])"),
        ("Medicine detail", "None", "Missing", "Needs implementation (per-unit price math, dosage form comparison, caution drug banner)"),
        ("Total", "None", "Missing", "Needs implementation (prescription total cost comparison and per-month savings calculation)"),
        ("Where to buy", "None", "Missing", "Needs implementation (link-out to official PMBI Kendra locator at pmbi.co.in)"),
        ("Learn", "None", "Missing", "Needs implementation (tab in nav: what is a salt, bioequivalence, PMBJP quality standards)"),
        ("About", "None", "Missing", "Needs implementation (tab in nav: project background, metrics from metrics.json, data date, disclaimer)"),
        ("Privacy", "None", "Missing", "Needs implementation (no photos stored, no accounts, no tracking, in-memory processing only)"),
        ("Help", "None", "Missing", "Needs implementation (frequently asked questions and user guidance)"),
        ("Settings", "None", "Missing", "Needs implementation (language switcher, large text mode toggle, dark theme toggle)"),
        ("Error", "None", "Missing", "Needs implementation (general error handling screen for network/server failure)"),
        ("Offline", "None", "Missing", "Needs implementation (PWA offline fallback banner and cache behavior)")
    ]

    # Problem Scanning across all files in design/_unzipped
    flagged_problems = {
        'a_photos_faces_medicine_text': [],
        'b_hardcoded_numbers': [],
        'c_false_risky_claims': [],
        'd_broken_logos_samasalt': [],
        'e_avatars_dup_language': [],
        'f_red_warnings': [],
        'g_external_resources': [],
        'h_text_under_14px': []
    }

    risky_claim_patterns = [
        r'Verified Equivalents',
        r'Public Health Utility',
        r'AI Prescription Reader',
        r'100% on-device',
        r'50% and 85%',
        r'50% to 90%',
        r'verified Labs',
        r'Data Dignity',
        r'Class 6 reading level',
        r'Step 2 of 3',
        r'certified manufacturers',
        r'certified',
        r'verified',
        r'guaranteed',
        r'official app'
    ]

    for root, dirs, files in os.walk(unzipped_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, unzipped_dir)
            
            if fname.endswith(('.html', '.md', '.json')):
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # (a) Photos / real medicine text
                if 'data-alt' in content or 'blister foil strip' in content.lower():
                    flagged_problems['a_photos_faces_medicine_text'].append((rel_path, "Viewfinder includes background medicine blister foil strip imagery / data-alt mockup description"))
                if 'Brandex 500' in content or 'Cardiofix 5' in content:
                    flagged_problems['a_photos_faces_medicine_text'].append((rel_path, "Mockup contains hardcoded medicine names 'Brandex 500 tablet' and 'Cardiofix 5'"))

                # (b) Hardcoded numbers
                num_matches = re.findall(r'(?:₹\s*\d+(?:\.\d+)?|\d+%\s*to\s*\d+%|\d+%\s*lower|\b500mg\b|\b625 Duo\b)', content)
                for nm in set(num_matches):
                    flagged_problems['b_hardcoded_numbers'].append((rel_path, f"Hardcoded price/percentage/strength: '{nm}'"))

                # (c) False or risky claims
                for pat in risky_claim_patterns:
                    for m in re.finditer(pat, content, re.I):
                        flagged_problems['c_false_risky_claims'].append((rel_path, f"Matched forbidden claim pattern: '{m.group(0)}'"))

                # (d) Broken logo images and old name "SamaSalt"
                if 'SamaSalt' in content or 'samasalt' in content.lower():
                    matches = set(re.findall(r'[Ss]ama[Ss]alt', content))
                    flagged_problems['d_broken_logos_samasalt'].append((rel_path, f"Found legacy brand name '{', '.join(matches)}'"))
                
                # Check broken images
                img_srcs = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', content)
                for src in img_srcs:
                    if not src.startswith(('data:', 'http')) and not os.path.exists(os.path.join(os.path.dirname(fpath), src)):
                        flagged_problems['d_broken_logos_samasalt'].append((rel_path, f"Potentially broken local image reference: '{src}'"))

                # (e) Profile avatars and duplicate language switchers
                if 'avatar' in content.lower():
                    flagged_problems['e_avatars_dup_language'].append((rel_path, "Found reference to user avatar in template"))
                if 'HI/EN' in content and 'lang-opt' in content:
                    flagged_problems['e_avatars_dup_language'].append((rel_path, "Duplicate language switcher present (header button + banner pill group)"))

                # (f) Red used for warnings / errors
                red_matches = set(re.findall(r'#(?:ba1a1a|ffdad6|93000a|ef4444|dc2626|b91c1c|red)\b|text-red|bg-red|border-red', content, re.I))
                if red_matches:
                    flagged_problems['f_red_warnings'].append((rel_path, f"Red styling detected: {', '.join(red_matches)}"))

                # (g) External resources
                ext_matches = set(re.findall(r'https?://[^\s\'"<>]+', content))
                for ext in ext_matches:
                    if any(domain in ext for domain in ['fonts.googleapis.com', 'fonts.gstatic.com', 'cdn.tailwindcss.com', 'ajax.googleapis.com']):
                        flagged_problems['g_external_resources'].append((rel_path, f"Remote CDN/Font resource: '{ext}'"))

                # (h) Text under 14px
                small_text = set(re.findall(r'\b(?:text-xs|text-\[1[0-3]px\]|font-size:\s*1[0-3]px|font-size:\s*[0-9]px)\b', content))
                if small_text:
                    flagged_problems['h_text_under_14px'].append((rel_path, f"Text scale below 14px: {', '.join(small_text)}"))

    # Extract design tokens from DESIGN.md and HTML
    design_tokens = {
        "spec": {
            "primary": "#0F766E",
            "background": "#FAF8F5",
            "accent": "#F28B6B",
            "font_family": "Inter, sans-serif",
            "border_radius": "16px",
            "borders": "1px solid #E2DED9",
            "elevation": "none (no shadows, no gradients)"
        },
        "stitch_export": {
            "colors": {
                "primary": "#005c55",
                "primary_container": "#0f766e",
                "surface": "#fbf9f6",
                "background": "#fbf9f6",
                "surface_container_lowest": "#ffffff",
                "outline": "#6e7977",
                "outline_variant": "#bdc9c6",
                "secondary": "#99462b",
                "secondary_container": "#fe9574",
                "error": "#ba1a1a",
                "error_container": "#ffdad6"
            },
            "status_system": {
                "exact_match": {"text": "#15803D", "bg": "#DCFCE7", "stroke": "#86EFAC"},
                "not_sure": {"text": "#B45309", "bg": "#FEF3C7", "stroke": "#FDE68A"},
                "no_match": {"text": "#475569", "bg": "#F1F5F9", "stroke": "#CBD5E1"},
                "unsupported": {"text": "#64748B", "bg": "#F8FAFC", "stroke": "#E2E8F0"}
            },
            "typography": {
                "headline_lg": "34px / 42px / 700 / -0.02em",
                "headline_lg_mobile": "32px / 40px / 700 / -0.02em",
                "title_md": "20px / 28px / 600 / -0.01em",
                "body_lg": "16px / 24px / 400",
                "body_lg_bold": "16px / 24px / 600",
                "label_md": "14px / 20px / 600",
                "label_sm": "14px / 20px / 500"
            },
            "radius": {
                "sm": "4px",
                "DEFAULT": "8px",
                "md": "12px",
                "lg": "16px",
                "xl": "24px",
                "full": "9999px"
            },
            "spacing": {
                "margin": "16px",
                "space_xs": "8px",
                "space_sm": "12px",
                "space_md": "16px",
                "space_lg": "24px",
                "space_xl": "32px"
            }
        },
        "differences": [
            "Primary Color: Export specifies primary as #005C55 and primary-container as #0F766E. Spec requires canonical #0F766E throughout.",
            "Surface/Canvas Color: Export uses #FBF9F6; Spec requires warmer #FAF8F5.",
            "Accent Coral: Export defines secondary as #99462B with container #FE9574; Spec mandates single accent coral #F28B6B.",
            "Outlines: Export specifies outline #6E7977 and #BDC9C6; Spec specifies architectural 1px borders #E2DED9.",
            "Shadows: Export includes drop shadows (shadow-sm, shadow-md, shadow-xl, ambient bottom shadow 0 4px 20px rgba(26,26,26,0.06)); Spec strictly mandates NO shadows.",
            "Gradients: Export includes multi-stop linear gradients in scanner and background scrims; Spec strictly mandates NO gradients.",
            "Corner Radii: Export includes 4px, 8px, 12px, 16px, 24px; Spec requires uniform 16px radius for all cards, buttons, inputs, and dialogs.",
            "Text Sizes: Export has 11px and 12px text in buttons and navigation; Spec enforces hard floor of 14px minimum.",
            "Red Error Palette: Export includes red error tokens (#BA1A1A, #93000A); Spec forbids red for alerts and warnings."
        ]
    }

    # Save tokens to json
    os.makedirs('design', exist_ok=True)
    with open('design/tokens.json', 'w', encoding='utf-8') as f:
        json.dump(design_tokens, f, indent=2)

    # Write INVENTORY.md
    inv_path = 'design/INVENTORY.md'
    with open(inv_path, 'w', encoding='utf-8') as f:
        f.write("# PillTwin Design Inventory & Gap Analysis\n\n")
        f.write(f"**Generated:** 2026-11-19  \n")
        f.write(f"**Source Directory:** `{unzipped_dir}`  \n")
        f.write(f"**Tokens File:** `design/tokens.json`  \n\n")

        f.write("## 1. Exported Screens & Assets Found\n\n")
        f.write("| Folder / Screen Name | HTML Template | PNG Preview | Design System Doc |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for sc in screens:
            f.write(f"| `{sc['name']}` | {'Yes (`code.html`)' if sc['has_html'] else 'No'} | {'Yes (`screen.png`)' if sc['has_png'] else 'No'} | {'Yes (`DESIGN.md`)' if sc['has_md'] else 'No'} |\n")
        f.write("\n")

        f.write("## 2. Complete User Flow Mapping & Coverage Gap\n\n")
        f.write("| Flow Step | Stitch Screen Found | Status in Export | Notes & Implementation Requirements |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for step, screen_found, status, notes in flow_steps:
            f.write(f"| **{step}** | `{screen_found}` | **{status}** | {notes} |\n")
        f.write("\n")

        f.write("## 3. Design Tokens Comparison & Specification Compliance\n\n")
        f.write("| Token Attribute | Project Spec | Stitch Exported Value | Status / Action |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write("| **Primary Color** | `#0F766E` (Teal) | `#005C55` (with `#0F766E` as container) | Align to canonical `#0F766E` |\n")
        f.write("| **Canvas / Background** | `#FAF8F5` (Warm off-white) | `#FBF9F6` | Correct to `#FAF8F5` |\n")
        f.write("| **Accent Color** | `#F28B6B` (Coral) | `#99462B` / `#FE9574` | Standardize to `#F28B6B` |\n")
        f.write("| **Typography** | Inter (14px to 34px) | Inter (includes 11px, 12px) | Remove sub-14px font sizes |\n")
        f.write("| **Corner Radius** | `16px` uniform | Mixed (`4px`, `8px`, `12px`, `16px`, `24px`) | Standardize all surfaces to `16px` |\n")
        f.write("| **Borders & Dividers** | `1px solid #E2DED9` | `1px solid #6E7977` / `#BDC9C6` | Use `#E2DED9` border architecture |\n")
        f.write("| **Drop Shadows** | **None** | `shadow-sm`, `shadow-md`, `shadow-xl`, ambient bar shadow | **Strip all shadows** |\n")
        f.write("| **Gradients** | **None** | Multiple linear gradients in camera view | **Replace with flat colors** |\n")
        f.write("| **Error / Warning Colors** | **No red** | `#BA1A1A`, `#FFDAD6` in design system | **Remove red tokens**; status only |\n\n")

        f.write("## 4. Flagged Problems in Stitch Exports (Items A-H)\n\n")

        def write_flags(category, title):
            items = flagged_problems[category]
            f.write(f"### {title} ({len(items)} items flagged)\n")
            if not items:
                f.write("None found.\n\n")
            else:
                for src, desc in items[:25]:
                    f.write(f"- **`{src}`**: {desc}\n")
                if len(items) > 25:
                    f.write(f"- *...and {len(items)-25} more instances.*\n")
                f.write("\n")

        write_flags('a_photos_faces_medicine_text', "A. Photos, Faces, or Readable Real Brand Text")
        write_flags('b_hardcoded_numbers', "B. Hardcoded Prices, Savings, Percentages, and Metrics")
        write_flags('c_false_risky_claims', "C. False, Marketing, or Legally Risky Claims")
        write_flags('d_broken_logos_samasalt', "D. Broken Images, Avatars, and Legacy 'SamaSalt' References")
        write_flags('e_avatars_dup_language', "E. Profile Avatars and Duplicate Language Switchers")
        write_flags('f_red_warnings', "F. Red Used for Warnings or Error Palettes")
        write_flags('g_external_resources', "G. External Resources (CDNs, Google Fonts, Scripts)")
        write_flags('h_text_under_14px', "H. Typography Scaling Under Accessible 14px Floor")

    print(f"Design inventory written to {inv_path}")

if __name__ == '__main__':
    audit_designs()
