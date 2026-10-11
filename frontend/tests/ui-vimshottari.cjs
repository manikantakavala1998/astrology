const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve(process.env.ASTRO_SCREENSHOTS || 'test-results');
fs.mkdirSync(output, { recursive: true });
const civil = value => Date.parse(`${value.slice(0, 23)}Z`);
const boundary = value => new Date(Math.ceil(civil(value) / 1000) * 1000).toISOString().slice(0, 19).replace(/:00$/, '');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1536, height: 1100 }, timezoneId: 'America/New_York' });
  page.setDefaultTimeout(60000);
  const errors = [], external = [], failed = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => { if (response.url().includes('/api/vimshottari/') && !response.ok()) failed.push(response.status()); });
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== origin) { external.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  const nav = label => page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: label, exact: true }).click();
  const loaded = () => page.waitForFunction(() => document.querySelectorAll('.vimshottari-period').length === 45);
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1).then(result => assert.ok(result));
  const selected = level => page.locator(`.vimshottari-level[data-level="${level}"] .vimshottari-period[aria-pressed="true"]`);
  try {
    await page.goto(origin);
    await page.locator('#birth_date').fill('04/09/1998');
    await page.locator('#birth_hour').selectOption('12');
    await page.locator('#birth_minute').selectOption('3');
    await page.locator('#birth_meridiem').selectOption('AM');
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#manual_latitude').fill('17.00517');
    await page.locator('#manual_longitude').fill('81.77784');
    await page.locator('#manual_utc_offset_hours').fill('5.5');
    const posted = page.waitForResponse(response => response.url() === `${origin}/` && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    const html = await (await posted).text();
    const state = JSON.parse(html.match(/<script id="astro-state" type="application\/json">([\s\S]*?)<\/script>/)[1]);
    await page.locator('.rasi-grid').waitFor();
    await nav('Dasha');
    await loaded();
    assert.equal(await page.getByRole('heading', { name: 'Prana', exact: true }).count(), 1);
    assert.equal(await page.locator('.vimshottari-period[aria-pressed="true"]').count(), 5);
    const explorer = page.locator('.vimshottari-explorer');
    const details = page.getByRole('region', { name: 'Selected dasha period details', exact: true });
    assert.ok((await explorer.boundingBox()).height <= 600, 'All 45 rows and selected details should fit a compact panel');
    const rowHeights = await page.locator('.vimshottari-period').evaluateAll(rows => rows.map(row => row.getBoundingClientRect().height));
    assert.ok(Math.max(...rowHeights) <= 44, 'Period rows should remain compact');
    assert.equal(await details.getAttribute('data-level'), '4');
    assert.equal(await details.getAttribute('data-start'), await selected(4).getAttribute('data-start'));
    assert.equal(await details.locator('time').first().getAttribute('datetime'), await selected(4).getAttribute('data-start'));
    for (const level of [3, 4]) assert.equal(await page.locator(`.vimshottari-level[data-level="${level}"] .vimshottari-period-dates small`).count(), 18);
    const date = page.getByLabel('Dasha viewing date & time');
    const first = state.vimshottari.periods[0];
    assert.equal(await page.locator('.vimshottari-level[data-level="0"] .vimshottari-period').first().getAttribute('data-start'), first.start);
    assert.equal(await page.locator('.vimshottari-level[data-level="0"] .vimshottari-period').count(), 9);
    await date.fill('1998-09-04T00:03');
    await loaded();
    for (let level = 0; level < 5; level++) {
      const start = await selected(level).getAttribute('data-start'), end = await selected(level).getAttribute('data-end');
      assert.ok(civil(start) <= civil('1998-09-04T00:03:00') && civil('1998-09-04T00:03:00') < civil(end));
      const planet = await selected(level).getAttribute('data-planet');
      assert.ok(await selected(level).locator(`.planet-color-${planet.toLowerCase()}`).isVisible());
      if (level > 0) {
        const parentStart = await selected(level - 1).getAttribute('data-start'), parentEnd = await selected(level - 1).getAttribute('data-end');
        const rows = page.locator(`.vimshottari-level[data-level="${level}"] .vimshottari-period`);
        assert.ok(Math.abs(civil(await rows.first().getAttribute('data-start')) - civil(parentStart)) <= 1);
        assert.ok(Math.abs(civil(await rows.last().getAttribute('data-end')) - civil(parentEnd)) <= 1);
      }
    }
    const second = state.vimshottari.periods[1];
    await selected(0).click();
    assert.equal(await details.getAttribute('data-level'), '0');
    await details.getByText('Calculation', { exact: true }).click();
    assert.match(await details.locator('details[open]').innerText(), /years × 365\.2425 days per year\. Remaining at birth:/);
    await details.getByText('Calculation', { exact: true }).click();
    await selected(4).click();
    const exactEnd = await selected(4).getAttribute('data-end');
    assert.ok((await details.innerText()).includes(exactEnd.slice(11, 19)), 'Full selected Prana seconds must be visible');
    await details.getByText('Calculation', { exact: true }).click();
    assert.match(await details.locator('details[open]').innerText(), /Parent .* days × .* \/ 120 ≈ .* days/);
    await details.getByText('Calculation', { exact: true }).click();
    await date.fill(boundary(second.start));
    await loaded();
    assert.equal(await selected(0).getAttribute('data-planet'), second.planet);
    // Manual selection opens a different branch, and rapid changes cancel stale work.
    const mains = page.locator('.vimshottari-level[data-level="0"] .vimshottari-period');
    await mains.nth(4).click();
    await mains.nth(8).click();
    await loaded();
    assert.equal(await selected(0).getAttribute('data-start'), state.vimshottari.periods[8].start);
    assert.equal(await details.getAttribute('data-level'), '0');
    assert.equal(await details.getAttribute('data-start'), state.vimshottari.periods[8].start);
    assert.equal(await details.locator('time').last().getAttribute('datetime'), state.vimshottari.periods[8].end);
    await page.getByRole('button', { name: 'Return to date’s sequence', exact: true }).click();
    await loaded();
    assert.equal(await selected(0).getAttribute('data-planet'), second.planet);
    await date.fill('1900-01-01T00:00');
    await loaded();
    assert.match(await page.locator('.vimshottari-notice').innerText(), /outside/);
    await date.fill('2026-10-09T12:00');
    await loaded();
    await page.screenshot({ path: path.join(output, 'vimshottari-dasha-desktop.png'), fullPage: true });
    await page.locator('.vimshottari-explorer').screenshot({ path: path.join(output, 'vimshottari-five-levels.png') });
    for (const width of [320, 390, 768, 1100, 1536]) {
      await page.setViewportSize({ width, height: 1000 });
      await overflow();
      const clipped = await page.locator('.vimshottari-period-name, .vimshottari-period-dates time, .vimshottari-selected-details dd').evaluateAll(nodes => nodes.filter(node => node.scrollWidth > node.clientWidth + 1).map(node => node.textContent));
      assert.deepEqual(clipped, [], `Short dates and full selected details must fit at ${width}px`);
      const scroller = page.locator('.vimshottari-columns-scroll');
      await scroller.evaluate(node => { node.scrollLeft = node.scrollWidth; });
      assert.ok(await page.getByRole('heading', { name: 'Prana', exact: true }).isVisible());
      const prana = await page.getByRole('heading', { name: 'Prana', exact: true }).boundingBox();
      assert.ok(prana.x + prana.width <= width + 1);
    }
    await page.setViewportSize({ width: 390, height: 1000 });
    await page.screenshot({ path: path.join(output, 'vimshottari-dasha-mobile.png'), fullPage: true });
    assert.deepEqual(errors, []); assert.deepEqual(external, []); assert.deepEqual(failed, []);
    console.log('PASS: compact panel and rows, selected exact times/calculations, all 45 periods through Prana, exact parent boundaries, birth/current/date selection, other browser timezone, branch races, planet colors, five widths, offline requests');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
