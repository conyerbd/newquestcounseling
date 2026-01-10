# New Quest Counseling - Project Instructions

## Overview
A static single-page website for New Quest Counseling, a therapy practice with a unique **gaming/RPG-inspired brand**. The site uses video game metaphors to make mental health services approachable and relatable.

- **Hosting:** GitHub Pages
- **Domain:** www.newquestcounseling.com
- **Tech Stack:** Single HTML file with Tailwind CSS (CDN), Font Awesome icons, Google Fonts, vanilla JavaScript

---

## Brand Colors

Use the `quest-*` Tailwind classes - never hardcode hex values:

| Class | Hex | Usage |
|-------|-----|-------|
| `quest-bg` | #FDFBF7 | Cream background, neutral sections |
| `quest-red` | #FF7F7F | Primary CTAs, alerts, important elements |
| `quest-blue` | #89CFF0 | Secondary accent, navigation, icons |
| `quest-green` | #98FF98 | Success indicators, checkmarks, progress |
| `quest-gold` | #FFD700 | Premium features, badges, highlights |
| `quest-dark` | #2D3748 | Primary text (headings, body) |
| `quest-slate` | #4A5568 | Secondary text, subheadings |
| `quest-card` | #FFFFFF | Cards, containers |

**Logo Colors:** Red "New Quest" + Blue "Counseling"

---

## Fonts

Use Tailwind font classes:

| Class | Font | Usage |
|-------|------|-------|
| `font-heading` | Nunito | Headings, navigation, buttons |
| `font-body` | Open Sans | Body text, descriptions |
| `font-pixel` | Press Start 2P | Accent labels, stats headers (use sparingly) |

---

## Content Tone & Style

### Voice
- **Approachable and empowering** - not clinical or intimidating
- **Gaming metaphors** throughout (but tastefully, not over-the-top)
- **Reassuring** - judgment-free, supportive messaging
- **Professional yet relatable** - mix clinical credentials with casual language

### Avoid
- Overly clinical/medical jargon
- Excessive gaming references that feel forced
- Anything that trivializes mental health struggles

---

## Design Patterns

### Components
- **Navigation:** Sticky with backdrop blur, mobile hamburger menu
- **Hero:** Floating decorative icons, dual CTA buttons
- **Cards:** Hover lift effect (translateY), border color change on hover
- **FAQ:** Accordion-style with smooth expand/collapse
- **Buttons:** Use `.btn-pixel` class for retro press effect

### Shadows
- `shadow-pixel` - 4px offset retro effect
- `shadow-pixel-hover` - 6px offset with blue tint

### Animations
- Transitions: 0.2-0.3s duration
- `float-anim` for floating elements
- Smooth scrolling enabled

### Responsive Breakpoints
Always test at:
- 375px (mobile)
- 768px (tablet)
- 1024px+ (desktop)

---

## Technical Notes

### File Structure
```
newquestcounseling/
├── .claude/instructions.md   (this file)
├── index.html                (entire website)
├── CNAME                     (custom domain)
├── .nojekyll                 (GitHub Pages config)
└── readme.md
```

### External Dependencies (CDN)
- Tailwind CSS (latest)
- Font Awesome 6.4.0
- Google Fonts (Nunito, Open Sans, Press Start 2P)

### JavaScript Features
1. Mobile menu toggle
2. FAQ accordion
3. Health bar scroll effect (color changes with scroll progress)

---

## Placeholders to Replace

These items need real content:
- [ ] Therapist photo (currently using placeholder API)
- [ ] Social media links (Discord, Instagram, Twitter point to #)
- [ ] Contact address and phone (currently dummy data)

---

## Development Guidelines

1. **Edit index.html directly** - no build process needed
2. **Keep it single-file** - all CSS/JS stays inline
3. **Test responsiveness** before committing
4. **Maintain gaming theme** but don't overdo it
5. **Preserve accessibility** - alt text, semantic HTML, proper contrast
6. **Push to main** to deploy (GitHub Pages auto-deploys)

---

## Recent Changes Log

- Toned down gamer verbiage (per recent commit)
- Domain setup finalized

---

*Last updated: January 2026*
