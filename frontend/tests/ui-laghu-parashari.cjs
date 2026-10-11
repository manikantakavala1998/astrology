const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1680, height: 1100 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
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
    const posted = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname === '/');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    const html = await (await posted).text();
    const state = JSON.parse(html.match(/<script id="astro-state" type="application\/json">([\s\S]*?)<\/script>/)[1]);
    const report = state.laghu_parashari;
    await page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: 'Laghu Parashari', exact: true }).click();
    const workspace = page.locator('.laghu-workspace');
    assert.equal(await workspace.getByRole('tab').count(), 6);
    assert.equal(await workspace.locator('.lp-table tbody tr').count(), 7);
    assert.match(await workspace.locator('.lp-table tbody tr').filter({ hasText: 'Saturn' }).innerText(), /Yogakaraka/);
    assert.match(await workspace.locator('.lp-table tbody tr').filter({ hasText: 'Venus' }).innerText(), /Mixed/);
    assert.match(await workspace.locator('.lp-table tbody tr').filter({ hasText: 'Mercury' }).innerText(), /Maraka role: H2/);
    await workspace.getByRole('button', { name: 'Venus', exact: true }).click();
    assert.match(await workspace.locator('.lp-bottom').innerText(), /Venus · rules & calculation/);
    const chart = await workspace.locator('.rasi-grid').boundingBox();
    assert.ok(chart.width <= 724 && chart.height <= 440);
    await page.screenshot({ path: path.resolve('test-results/laghu-parashari-implemented.png'), fullPage: true });
    await workspace.getByRole('tab', { name: 'All 12 ascendants', exact: true }).click();
    for (const entry of report.all_ascendants) {
      await workspace.locator('select').selectOption(entry.ascendant);
      const rows = await workspace.locator('.lp-table tbody tr').allTextContents();
      assert.equal(rows.length, 7);
      for (let index = 0; index < rows.length; index++) assert.ok(rows[index].includes(entry.roles[index].role));
    }
    await workspace.getByRole('tab', { name: 'Yogakaraka & Raja Yoga', exact: true }).click();
    assert.equal(await workspace.locator('.lp-aspects tbody tr').count(), 13);
    await workspace.getByRole('tab', { name: 'Dasha & Antardasha', exact: true }).click();
    assert.match(await workspace.locator('.lp-period-grid tbody tr').first().locator('td').nth(1).innerText(), /^\d{2}\/\d{2}\/\d{4}$/);
    const selected = report.periods.findIndex(p => p.start <= state.current_dasha.as_of && state.current_dasha.as_of < p.end);
    assert.match(await workspace.locator('.lp-period-grid > div').first().locator('tr[aria-selected="true"]').innerText(), new RegExp(report.periods[selected].planet));
    for (const major of report.periods) {
      await workspace.locator('.lp-period-grid > div').first().getByRole('button', { name: major.planet, exact: true }).click();
      assert.match(await workspace.locator('.lp-reading h3').innerText(), new RegExp(`^${major.planet} /`));
      const minor = major.sub_periods[3];
      await workspace.locator('.lp-period-grid > div').nth(1).getByRole('button', { name: minor.planet, exact: true }).click();
      assert.equal(await workspace.locator('.lp-reading h3').innerText(), `${major.planet} / ${minor.planet}`);
      assert.ok((await workspace.locator('.lp-reading').innerText()).includes(minor.reading.result));
    }
    await workspace.locator('input[type="datetime-local"]').fill('1800-01-01T00:00');
    assert.equal(await workspace.locator('.lp-reading').count(), 0);
    assert.ok((await workspace.innerText()).includes('outside the calculated'));
    await workspace.getByRole('button', { name: 'Today', exact: true }).click();
    assert.equal(await workspace.locator('.lp-reading').count(), 1);
    await page.screenshot({ path: path.resolve('test-results/laghu-parashari-periods.png'), fullPage: true });
    await workspace.getByRole('tab', { name: 'Maraka rules', exact: true }).click();
    assert.equal(await workspace.locator('tbody tr').count(), report.maraka_candidates.length);
    await workspace.getByRole('tab', { name: 'All rules', exact: true }).click();
    assert.equal(await workspace.locator('.lp-rule-detail').count(), 42);
    const exception = workspace.locator('.lp-rule-detail').filter({ hasText: 'Saturn–Venus exception' });
    await exception.locator('summary').click();
    assert.ok((await exception.innerText()).includes('no automatic good/bad inversion'));
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      for (const name of ['Your Lagna', 'All 12 ascendants', 'Yogakaraka & Raja Yoga', 'Dasha & Antardasha', 'Maraka rules', 'All rules']) {
        await workspace.getByRole('tab', { name, exact: true }).click();
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${name}: mobile width ${width}`);
      }
    }
    assert.deepEqual(errors, []);
    console.log('PASS: all six views, twelve ascendants, 42 rules, aspects, period boundaries and out-of-range dates, planet selection, desktop/mobile layout');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
