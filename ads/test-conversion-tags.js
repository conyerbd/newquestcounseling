/**
 * Verify that the Google Ads conversion tags actually fire, without waiting on
 * Google Ads reporting and without recording real conversions.
 *
 * Serves the working tree over localhost and drives it in a headless browser.
 * The conversion beacons are intercepted, recorded, and then ABORTED, so we
 * see that the tag fired but Google never receives it. That means this is safe
 * to run as often as you like against your own working copy.
 *
 *   node ads/test-conversion-tags.js
 *   node ads/test-conversion-tags.js --headful   # watch it happen
 *
 * Exits non-zero if any expected conversion did not fire.
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const puppeteer = require('./node_modules/puppeteer');

const ROOT = path.resolve(__dirname, '..');
const HEADFUL = process.argv.includes('--headful');

const OPEN_LABEL = 'gxwRCK7RqeccEIikg8hE';   // action 7732881582, Contact form opened
const SUBMIT_LABEL = 'rRBlCLq1rOccEIikg8hE'; // action 7732927162, Contact form submitted

// index.html requires the modal to sit open this long before a close counts as
// a submission. Kept in sync by hand; see MIN_FILL_SECONDS in index.html.
const MIN_FILL_SECONDS = 10;

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.json': 'application/json', '.ico': 'image/x-icon',
};

function serve() {
  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
    const file = path.join(ROOT, rel);
    // Keep the server inside the repo even if a page asks for something odd.
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404).end('not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise(resolve => {
    server.listen(0, '127.0.0.1', () => resolve({ server, port: server.address().port }));
  });
}

const isConversionBeacon = url =>
  /googleads\.g\.doubleclick\.net\/pagead\/viewthroughconversion|google\.com\/pagead\/1p-conversion|googleadservices\.com\/pagead\/conversion/.test(url);

// The label rides in the URL as .../viewthroughconversion/<id>/?...&label=<label>
// on some variants and as a `label` query param on others, so check both.
function labelsIn(url) {
  const found = new Set();
  for (const l of [OPEN_LABEL, SUBMIT_LABEL]) if (url.includes(l)) found.add(l);
  return [...found];
}

async function newPage(browser, fired) {
  const page = await browser.newPage();
  await page.setRequestInterception(true);
  page.on('request', req => {
    const url = req.url();
    if (isConversionBeacon(url)) {
      for (const l of labelsIn(url)) fired.push({ label: l, url });
      // Abort so Google never records this as a real conversion.
      return req.abort();
    }
    // The SimplePractice widget is slow and irrelevant to what we measure.
    if (url.includes('clientsecure.me') || url.includes('facebook')) return req.abort();
    req.continue();
  });
  page.on('pageerror', e => console.log(`    [page error] ${e.message}`));
  return page;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const { server, port } = await serve();
  const base = `http://127.0.0.1:${port}`;
  console.log(`Serving ${ROOT} on ${base}\n`);

  const browser = await puppeteer.launch({
    headless: !HEADFUL,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  const results = [];
  const check = (name, pass, detail) => {
    results.push({ name, pass, detail });
    console.log(`  ${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? `\n        ${detail}` : ''}`);
  };

  try {
    // --- Test 1: thank-you.html fires the submit conversion on page load ---
    console.log('Test 1: thank-you.html page load');
    {
      const fired = [];
      const page = await newPage(browser, fired);
      await page.goto(`${base}/thank-you.html`, { waitUntil: 'networkidle2' });
      await sleep(1500);
      check('submit conversion fires on thank-you.html',
        fired.some(f => f.label === SUBMIT_LABEL),
        `saw: ${fired.map(f => f.label).join(', ') || 'nothing'}`);
      check('open conversion does NOT fire on thank-you.html',
        !fired.some(f => f.label === OPEN_LABEL));
      await page.close();
    }

    // --- Test 2: opening the contact form fires the open conversion --------
    console.log('\nTest 2: index.html, open the contact form');
    {
      const fired = [];
      const page = await newPage(browser, fired);
      await page.goto(`${base}/index.html`, { waitUntil: 'networkidle2' });
      await page.click('button[data-nq-event="open-contact-form"]');
      await sleep(1500);
      check('open conversion fires when the modal opens',
        fired.some(f => f.label === OPEN_LABEL),
        `saw: ${fired.map(f => f.label).join(', ') || 'nothing'}`);
      check('modal is actually visible',
        !(await page.$eval('#contact-modal', el => el.classList.contains('hidden'))));

      // Close and reopen: the once-per-pageview guard should hold.
      const before = fired.filter(f => f.label === OPEN_LABEL).length;
      await page.click('#contact-modal-close');
      await sleep(300);
      await page.click('button[data-nq-event="open-contact-form"]');
      await sleep(1000);
      check('reopening does not double count',
        fired.filter(f => f.label === OPEN_LABEL).length === before,
        `fired ${fired.filter(f => f.label === OPEN_LABEL).length}x total`);
      await page.close();
    }

    // --- Test 3: the full handoff, which is the one that matters -----------
    console.log(`\nTest 3: open the form, wait ${MIN_FILL_SECONDS + 1}s, close it`);
    {
      const fired = [];
      const page = await newPage(browser, fired);
      await page.goto(`${base}/index.html`, { waitUntil: 'networkidle2' });
      await page.click('button[data-nq-event="open-contact-form"]');
      console.log(`  waiting ${MIN_FILL_SECONDS + 1}s...`);
      await sleep((MIN_FILL_SECONDS + 1) * 1000);
      await page.click('#contact-modal-close');
      await sleep(2500);
      check('lands on thank-you.html after a long-enough session',
        page.url().includes('thank-you.html'),
        `url: ${page.url()}`);
      check('submit conversion fires at the end of the flow',
        fired.some(f => f.label === SUBMIT_LABEL),
        `saw: ${fired.map(f => f.label).join(', ') || 'nothing'}`);
      await page.close();
    }

    // --- Test 4: a quick close should NOT count as a submission -----------
    console.log('\nTest 4: open and close immediately');
    {
      const fired = [];
      const page = await newPage(browser, fired);
      await page.goto(`${base}/index.html`, { waitUntil: 'networkidle2' });
      await page.click('button[data-nq-event="open-contact-form"]');
      await sleep(500);
      await page.click('#contact-modal-close');
      await sleep(2000);
      check('does not hand off to thank-you.html',
        !page.url().includes('thank-you.html'),
        `url: ${page.url()}`);
      check('submit conversion does NOT fire',
        !fired.some(f => f.label === SUBMIT_LABEL));
      await page.close();
    }
  } finally {
    await browser.close();
    server.close();
  }

  const failed = results.filter(r => !r.pass);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed.`);
  if (failed.length) {
    console.log('\nFailed:');
    for (const f of failed) console.log(`  - ${f.name}`);
  }
  console.log('\nAll conversion beacons were aborted, so nothing reached Google Ads.');
  process.exit(failed.length ? 1 : 0);
})();
