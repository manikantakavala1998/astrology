const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve(process.env.ASTRO_SCREENSHOTS || 'test-results');
fs.mkdirSync(output, { recursive: true });
const signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
const expectedLagna = [5, 3, 4, 6, 3, 4, 5, 4, 5, 3, 3, 4];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1860, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const nav = label => page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: label, exact: true }).click();
  async function verifyCells(selector) {
    const failures = await page.locator(selector).evaluateAll(cells => cells.flatMap(cell => {
      const header = cell.querySelector('.cell-sign').getBoundingClientRect();
      const value = cell.querySelector('.cell-bindus').getBoundingClientRect();
      const bounds = cell.getBoundingClientRect();
      return value.top < header.bottom - 1 || value.bottom > bounds.bottom + 1 || header.left < bounds.left - 1 || header.right > bounds.right + 1
        ? [{ text: cell.textContent.trim(), viewport: innerWidth, header: header.toJSON(), value: value.toJSON(), bounds: bounds.toJSON() }] : [];
    }));
    if (failures.length) await page.screenshot({ path: path.join(output, 'ashtakavarga-overlap-failure.png') });
    assert.deepEqual(failures, [], 'Sign, house and score stay visible without overlap');
  }
  try {
    await page.goto(origin);
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
    await page.locator('.rasi-grid').waitFor();
    await nav('Ashtakavarga');
    const lagna = page.locator('#panel-ashtakavarga [data-ashtaka-planet="Lagna"]');
    assert.equal(await page.locator('#panel-ashtakavarga .mini-chart-grid').count(), 9);
    assert.equal(await page.locator('#panel-ashtakavarga .held-chart-notice').count(), 0);
    for (const [index, sign] of signs.entries()) {
      assert.equal(await lagna.locator(`[data-sign="${sign}"]`).getAttribute('data-bindus'), String(expectedLagna[index]));
    }
    assert.match(await lagna.textContent(), /Natal Taurus: 3 bindus.*Total 49/);
    const rules = page.locator('.lagna-ashtaka-rules');
    await rules.locator('summary').click();
    const contributionRows = rules.getByRole('table', { name: 'Lagna Ashtakavarga contribution rules' }).locator('tbody tr');
    const scoreRows = rules.getByRole('table', { name: 'Lagna Ashtakavarga sign calculations' }).locator('tbody tr');
    assert.equal(await contributionRows.count(), 8);
    assert.equal(await scoreRows.count(), 12);
    assert.equal(await contributionRows.filter({ has: page.getByRole('cell', { name: 'Moon', exact: true }) }).locator('td').nth(3).textContent(), '5');
    const taurus = scoreRows.filter({ has: page.getByRole('cell', { name: 'Taurus', exact: true }) });
    assert.equal(await taurus.locator('td').nth(1).textContent(), 'H1');
    assert.equal(await taurus.locator('td').nth(2).textContent(), 'Sun, Mars, Mercury');
    assert.equal(await taurus.locator('td').nth(3).textContent(), '3');
    await rules.locator('summary').click();
    for (const width of [1860, 1366, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      await verifyCells('#panel-ashtakavarga .mini-chart-cell:not(.blank)');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    await page.setViewportSize({ width: 1860, height: 1000 });
    await page.locator('#panel-ashtakavarga .panel').first().screenshot({ path: path.join(output, 'lagna-ashtakavarga-enabled.png') });
    await nav('Brihat Jataka');
    await page.getByRole('navigation', { name: 'Brihat Jataka views' }).getByRole('button', { name: /Ashtakavarga/ }).click();
    assert.equal(await page.locator('.bj-ashtaka-charts .mini-chart-grid').count(), 8);
    const desktop = await page.locator('.bj-ashtaka-charts .mini-chart-grid').first().boundingBox();
    assert.ok(desktop.width > 240 && desktop.width <= 260, 'Brihat bindu charts are slightly larger than the previous 220px size');
    assert.ok(desktop.height < 165, 'The wider chart stays compact');
    for (const width of [1860, 1366, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      await verifyCells('.bj-ashtaka-charts .mini-chart-cell:not(.blank)');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    await page.setViewportSize({ width: 1860, height: 1000 });
    await page.locator('.bj-ashtaka-charts').screenshot({ path: path.join(output, 'brihat-ashtakavarga-slightly-larger.png') });
    assert.deepEqual(errors, []);
    console.log('PASS: Lagna 49-point calculation and contributor arithmetic; SAV remains separate; nine Parasara charts; eight slightly larger Brihat charts; 320–1860px layouts');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
