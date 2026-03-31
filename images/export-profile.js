const puppeteer = require('../ads/node_modules/puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    await page.setViewport({ width: 512, height: 512, deviceScaleFactor: 2 });

    const filePath = path.resolve(__dirname, 'fb-profile.html');
    await page.goto(`file://${filePath}`, { waitUntil: 'networkidle0' });

    await page.evaluate(() => {
        document.body.style.padding = '0';
        document.body.style.margin = '0';
        document.body.style.minHeight = '512px';
    });

    await page.screenshot({
        path: path.resolve(__dirname, 'fb-profile.png'),
        type: 'png',
        clip: { x: 0, y: 0, width: 512, height: 512 },
    });

    console.log('Exported fb-profile.png (512x512)');
    await browser.close();
})();
