import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const root = process.env.REPO_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const url = process.env.SCREENSHOT_URL || 'http://127.0.0.1:8765/';

const hideScroll = `
  html, body {
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
    overflow-x: hidden !important;
  }
  *::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
  }
`;

const shots = [
  ['home-desktop.png', 1280, 800],
  ['home-mobile.png', 390, 844],
];

const browser = await chromium.launch();
for (const [name, width, height] of shots) {
  const context = await browser.newContext({
    bypassCSP: true,
    viewport: { width, height },
    deviceScaleFactor: 2,
    isMobile: width < 600,
    hasTouch: width < 600,
  });
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await page.addStyleTag({ content: hideScroll });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(400);
  const out = path.join(root, 'docs/screenshots', name);
  await page.screenshot({ path: out, type: 'png' });
  console.log('Wrote', out);
  await context.close();
}
await browser.close();
