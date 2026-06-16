const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const pagesToVisit = [
    { name: 'CIO', url: 'http://localhost:3000/' },
    { name: 'Portfolio', url: 'http://localhost:3000/portfolio' },
    { name: 'Post Mortem', url: 'http://localhost:3000/oversight' },
    { name: 'Performance', url: 'http://localhost:3000/performance' },
    { name: 'Research', url: 'http://localhost:3000/research' },
    { name: 'Theses', url: 'http://localhost:3000/theses' },
    { name: 'Analysts', url: 'http://localhost:3000/analysts' }
  ];

  for (const pageInfo of pagesToVisit) {
    console.log(`\n--- Navigating to ${pageInfo.name} (${pageInfo.url}) ---`);
    const page = await browser.newPage();
    
    // Capture console messages
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log(`[Browser Console Error] ${msg.text()}`);
      } else {
        // console.log(`[Browser Console] ${msg.type()}: ${msg.text()}`);
      }
    });

    // Capture uncaught exceptions
    page.on('pageerror', err => {
      console.log(`[Browser Uncaught Exception] ${err.message}`);
    });

    // Capture network requests to our API
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        console.log(`[Browser Network] Request: ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (response.url().includes('/api/')) {
        console.log(`[Browser Network] Response: ${response.status()} ${response.url()}`);
      }
    });

    await page.goto(pageInfo.url, { waitUntil: 'networkidle' });
    await page.close();
  }

  await browser.close();
})();
