const puppeteer = require('../ads/node_modules/puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    await page.setViewport({ width: 820, height: 462, deviceScaleFactor: 2 });

    const filePath = path.resolve(__dirname, 'fb-banner.html');
    await page.goto(`file://${filePath}`, { waitUntil: 'networkidle0' });

    await page.evaluate(() => {
        document.body.style.padding = '0';
        document.body.style.margin = '0';
        document.body.style.minHeight = '462px';
    });

    await page.screenshot({
        path: path.resolve(__dirname, 'fb-banner.png'),
        type: 'png',
        clip: { x: 0, y: 0, width: 820, height: 462 },
    });

    console.log('Exported fb-banner.png (820x462)');
    await browser.close();
})();
