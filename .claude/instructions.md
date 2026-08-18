# New Quest Counseling - Project Instructions

## Overview
A static website for New Quest Counseling, the Cincinnati therapy practice of **Dorasae Rosario, LPCC**. The brand uses a light gaming/RPG theme to make mental health services approachable — video game metaphors, a "character sheet" bio, a scroll-progress "health bar."

- **Hosting:** GitHub Pages (push to `main` to deploy)
- **Domain:** www.newquestcounseling.com (apex and `http://` both 301 to `https://www.`)
- **Tech Stack:** Two hand-written HTML files with Tailwind CSS (CDN), Font Awesome, Google Fonts, vanilla JS. No build step.
- **Practice details:** Cincinnati, OH; licensed statewide in Ohio; sessions are virtual. Phone (513) 622-9072, dorasae@newquestcounseling.com.
- **Insurance:** In-network with **Anthem** and **UnitedHealthcare** (one word — official brand spelling). Sliding-scale self-pay also offered.

---

## Brand Colors

Use the `quest-*` Tailwind classes — never hardcode hex values in markup.

| Class | Hex | Usage |
|-------|-----|-------|
| `quest-bg` | #B3D4E8 | Light blue page background |
| `quest-red` | #E85A8F | Heart pink — **large** CTAs only (18px+ bold) |
| `quest-red-dark` | #C9265F | Pink for **small** text/buttons on color (5.35:1 vs white) |
| `quest-blue` | #1A3A5C | Navy — outlines, icons, secondary buttons |
| `quest-green` | #98FF98 | Success checkmarks, health bar high state |
| `quest-gold` | #F7D426 | Lightning yellow — badges, accents |
| `quest-dark` | #1A3A5C | Primary text, dark section backgrounds |
| `quest-slate` | #2A4460 | Secondary text |
| `quest-card` | #FFFFFF | Cards, containers |

**Contrast rule:** `quest-red` on white is only 3.34:1 — it passes WCAG AA for large text (18.66px+ bold / 24px+) but **fails for anything smaller**. Use `quest-red-dark` for `text-sm`/`text-xs` buttons, badges, and body-size links. Same for yellow: `text-yellow-600` fails on white; use `text-yellow-700` or darker.

**Logo colors:** the logo is a yellow lightning bolt + yellow "NEW QUEST COUNSELING" wordmark with a white keyline and navy outline (`#ffe000`, `#ffffff`, `#004098`, `#ff6492`). Because the fill is yellow and white, it reads fine on both the light background and the navy footer.

---

## Fonts

| Class | Font | Usage |
|-------|------|-------|
| `font-heading` | Nunito | Headings, navigation, buttons |
| `font-body` | Open Sans | Body text, descriptions |
| `font-pixel` | Press Start 2P | Accent labels, section eyebrows (use sparingly) |

---

## Content Tone & Style

### Voice
- **Approachable and empowering** — not clinical or intimidating
- **Gaming metaphors** throughout, but tastefully
- **Reassuring** — judgment-free, supportive
- **Professional yet relatable** — clinical credentials mixed with casual language

### Avoid
- Overly clinical/medical jargon
- Gaming references that feel forced
- Anything that trivializes mental health struggles

---

## File Structure

```
newquestcounseling/
├── .claude/instructions.md   (this file)
├── index.html                (home: hero, problems, services, insurance, FAQ, contact)
├── about.html                 (therapist bio / "character sheet")
├── favicon.svg                (navy square + yellow bolt; hand-drawn for 16px legibility)
├── og-image.png               (1200x630 social/ad share card)
├── logo.svg                   (main logo, precision-optimized)
├── logo-w-bg.jpg              (logo on solid background)
├── headshot.jpg               (1000x923, q82)
├── robots.txt / sitemap.xml
├── CNAME / .nojekyll
├── ads/                       (Meta ad creatives + puppeteer exporter)
└── images/                    (FB banner/profile + og-image templates & exporters)
```

### External Dependencies (CDN)
- Tailwind CSS via `cdn.tailwindcss.com` — this is the runtime JIT build, not a compiled stylesheet. It logs a production warning and means styles depend on third-party JS. Accepted tradeoff to keep the no-build, single-file-per-page setup.
- Font Awesome 6.4.0
- Google Fonts (Nunito, Open Sans, Press Start 2P)

---

## Design Patterns

- **Navigation:** Sticky, centered logo, collapses the logo row on scroll. Mobile hamburger.
- **Hero:** Floating decorative icons, dual CTAs, location + insurance trust lines.
- **Cards:** Hover lift (`-translate-y`), border color change on hover.
- **FAQ:** Accordion; each toggle is a real `<button>` with `aria-expanded`.
- **Contact:** Opens the SimplePractice form in a modal iframe (loaded lazily on open).
- **Buttons:** `.btn-pixel` for the retro press effect.
- **Shadows:** `shadow-pixel` (4px offset), `shadow-pixel-hover` (6px, pink tint).
- **Animations:** 0.2–0.3s transitions; `float-anim` for floating elements.

### Responsive Breakpoints
Always check 375px (mobile), 768px (tablet), 1024px+ (desktop).

---

## JavaScript Features

Both pages share: mobile menu toggle (syncs `aria-expanded`/`aria-label`), nav collapse on scroll, health-bar scroll progress (pink → yellow → green).
`index.html` additionally has: FAQ accordion, contact modal (Escape to close, focus moves in and returns on close), and Meta Pixel event tracking.

---

## Analytics

Meta Pixel `1395723405642951` is on both pages. Events:
- `PageView` — both pages
- `ViewContent` — About page load; Services and FAQ sections on scroll into view (fires once each)
- `Schedule` — clicks on any `a[href="#contact"]`
- `Contact` — contact modal opened

When adding a CTA that should be tracked, point it at `#contact` so it picks up `Schedule` automatically.

---

## SEO / Social

Both pages carry: `meta description`, `canonical`, `theme-color`, favicon links, full Open Graph + Twitter card tags, and JSON-LD structured data (`ProfessionalService`/`MedicalBusiness` on the home page, `ProfilePage` on about). `og-image.png` is the 1200x630 share card — regenerate it from `images/og-image.html` if the messaging or accepted insurance changes.

**When editing insurance, phone, email, or location, update all of these:** the hero trust line, the "Insurance Accepted" block, the insurance FAQ, the contact section, the `meta description`/OG/Twitter descriptions, the JSON-LD, and `images/og-image.html` (then re-export `og-image.png`).

---

## Asset Notes

- `logo.svg` is ~584KB of path data (down from 924KB) — numeric precision was reduced to 2 decimals, which is visually identical at every size the site uses. It has no raster data, so it can't compress much further without a redraw. It's referenced twice per page but cached after the first request.
- `headshot.jpg` is 1000x923 at q82 (~120KB, down from 428KB). The about page displays it in a 3:4 `object-cover` box roughly 340px wide, so this is comfortably 2x for retina.
- Below-the-fold images use `loading="lazy"`; the nav logo uses `fetchpriority="high"`. All have explicit `width`/`height` to prevent layout shift.
- `ads/logo.svg` is a copy of the root logo — keep them in sync.

---

## Development Guidelines

1. **Edit the HTML directly** — no build process.
2. **Keep CSS/JS inline** per page; the two pages intentionally duplicate the shared nav/footer/JS. When you change one, check whether the other needs the same change.
3. **Test responsiveness** before committing.
4. **Maintain the gaming theme** but don't overdo it.
5. **Preserve accessibility** — alt text, semantic HTML, `aria-hidden="true"` on decorative Font Awesome icons, `aria-expanded` on disclosure controls, and the contrast rule above.
6. **Push to `main`** to deploy.

---

*Last updated: August 2026*
