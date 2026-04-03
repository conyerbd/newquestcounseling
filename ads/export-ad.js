const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    // Set viewport to exactly 1080x1080 with no padding
    await page.setViewport({ width: 1080, height: 1080, deviceScaleFactor: 1 });

    const filePath = path.resolve(__dirname, 'ad1.html');
    await page.goto(`file://${filePath}`, { waitUntil: 'networkidle0' });

    // Remove body padding so the ad fills the viewport exactly
    await page.evaluate(() => {
        document.body.style.padding = '0';
        document.body.style.margin = '0';
        document.body.style.minHeight = '1080px';
    });

    // Full page clip at 1080x1080 — captures the navy background behind rounded corners
    await page.screenshot({
        path: path.resolve(__dirname, 'ad1.png'),
        type: 'png',
        clip: { x: 0, y: 0, width: 1080, height: 1080 },
    });

    console.log('Exported ad1.png (1080x1080)');

    // Export vertical version (1080x1920) for Stories/Reels
    await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });

    const verticalPath = path.resolve(__dirname, 'ad1-vertical.html');
    await page.goto(`file://${verticalPath}`, { waitUntil: 'networkidle0' });

    await page.evaluate(() => {
        document.body.style.padding = '0';
        document.body.style.margin = '0';
        document.body.style.minHeight = '1920px';
    });

    await page.screenshot({
        path: path.resolve(__dirname, 'ad1-vertical.png'),
        type: 'png',
        clip: { x: 0, y: 0, width: 1080, height: 1920 },
    });

    console.log('Exported ad1-vertical.png (1080x1920)');
    await browser.close();
})();
