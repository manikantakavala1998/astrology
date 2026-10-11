const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1860, height: 1040 } });
    await page.goto('http://127.0.0.1:8765/');
    await page.locator('#name').fill('Manikanta Kavala');
    await page.locator('#birth_date').fill('04/09/1998');
    await page.locator('#birth_hour').selectOption('12');
    await page.locator('#birth_minute').selectOption('3');
    await page.locator('#birth_meridiem').selectOption('AM');
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#manual_latitude').fill('17.00517');
    await page.locator('#manual_longitude').fill('81.77784');
    await page.locator('#manual_utc_offset_hours').fill('5.5');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('#panel-chart .rasi-grid').waitFor();
    const nav = async label => {
      if (page.viewportSize().width < 780) await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
      await page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: label, exact: true }).click();
    };
    for (const variant of ['react', 'server']) {
      await page.setViewportSize({ width: 1860, height: 1040 });
      if (variant === 'server') {
        await nav('Divisional charts');
        await page.getByRole('tab', { name: 'D2', exact: true }).click();
      }
      const selector = variant === 'react' ? '#panel-chart .rasi-grid' : '#panel-divisional .subtab-panel:visible .chart-grid';
      const grid = page.locator(selector);
      const original = await grid.evaluate(element => element.outerHTML);
      // Only the browser fixture moves entries. All grahas, degrees and flags
      // are kept, including a tenth row for the ascendant, the maximum density.
      await grid.evaluate(element => {
        const cells = [...element.querySelectorAll('.rasi-cell, .chart-cell:not(.blank)')];
        const rows = [...element.querySelectorAll('.chart-planet-row')].map(row => row.cloneNode(true));
        const target = cells.find(cell => cell.querySelector('.chart-sign-full').textContent === 'Leo');
        cells.forEach(cell => cell.querySelector('.rasi-planets, .cell-planets').replaceChildren());
        const ascendant = rows.find(row => row.classList.contains('rasi-asc') || row.classList.contains('cell-asc'));
        const planets = rows.filter(row => row !== ascendant);
        target.querySelector('.rasi-planets, .cell-planets').replaceChildren(ascendant, ...planets);
        target.dataset.crowdedFixture = 'true';
        element.style.setProperty('--chart-slots', '10');
      });
      for (const width of [1860, 1366, 390, 320]) {
        await page.setViewportSize({ width, height: 1040 });
        const result = await grid.locator('[data-crowded-fixture]').evaluate(cell => {
          const c = cell.getBoundingClientRect();
          const rows = [...cell.querySelectorAll('.chart-planet-row')];
          const rectangles = rows.map(row => row.getBoundingClientRect());
          const crossing = rows.flatMap(row => [...row.children]).filter(child => {
            const r = child.getBoundingClientRect();
            return r.left < c.left + 1 || r.right > c.right - 1 || r.top < c.top + 1 || r.bottom > c.bottom - 1;
          }).map(child => child.textContent);
          const overlapping = rows.filter((row, index) => rectangles.some((b, second) => {
            if (index >= second) return false;
            const a = rectangles[index];
            return Math.min(a.right, b.right) - Math.max(a.left, b.left) > .5 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > .5;
          })).map(row => row.textContent);
          return { count: rows.length, crossing, overlapping, font: getComputedStyle(rows[0]).fontSize, cellHeight: c.height,
            lastBottom: rectangles[rectangles.length - 1].bottom - c.top };
        });
        await page.screenshot({ path: path.resolve(`test-results/crowded-${variant}-${width}.png`) });
        assert.equal(result.count, 10);
        assert.deepEqual(result.crossing, [], `${variant} at ${width}: ${JSON.stringify(result)}`);
        assert.deepEqual(result.overlapping, [], `${variant} at ${width}: ${JSON.stringify(result)}`);
        const bounds = await grid.boundingBox();
        assert.ok(bounds.width <= 724 + 1 && bounds.height <= 440 + 1);
        console.log(`PASS: ${variant} ${width}px, all 10 entries fit without crossing borders`);
      }
      await grid.evaluate((element, html) => element.outerHTML = html, original);
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
