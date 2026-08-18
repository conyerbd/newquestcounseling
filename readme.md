# New Quest Counseling

Marketing site for [New Quest Counseling](https://www.newquestcounseling.com) — the Cincinnati therapy practice of Dorasae Rosario, LPCC.

Static site, no build step. Two hand-written HTML pages using Tailwind CSS via CDN, Font Awesome, and Google Fonts.

## Structure

| File | Purpose |
|------|---------|
| `index.html` | Home — hero, problem cards, services, insurance, FAQ, contact |
| `about.html` | Therapist bio, styled as an RPG "character sheet" |
| `og-image.png` | 1200x630 social/ad share card (template: `images/og-image.html`) |
| `favicon.svg` | Navy square with the brand lightning bolt |
| `ads/` | Meta ad creatives and their Puppeteer exporter |
| `images/` | Facebook banner/profile art, share-card templates, exporters |

## Local development

Open `index.html` in a browser — there's nothing to compile. For anything involving relative paths or the contact iframe, serve it instead:

```sh
npx serve .
```

## Deploying

GitHub Pages serves `main` directly. Push to deploy:

```sh
git push origin main
```

`CNAME` pins the custom domain and `.nojekyll` disables Jekyll processing.

## Regenerating images

The share card and ad creatives are rendered from HTML templates via headless Chrome:

```sh
cd ads && npm install && node export-ad.js
cd images && node export-banner.js && node export-profile.js
```

`og-image.png` is rendered from `images/og-image.html` at 1200x630. Re-export it whenever the headline, location, or accepted insurance changes.

## Conventions

See [`.claude/instructions.md`](.claude/instructions.md) for brand colors, the contrast rules for the pink palette, tone guidance, analytics events, and the checklist of places to update when practice details change.
