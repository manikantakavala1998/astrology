const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve(process.env.ASTRO_SCREENSHOTS || 'test-results');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const nav = label => page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: label, exact: true }).click();
  async function unclipped(selector) {
    const clipped = await page.locator(selector).evaluateAll(cells => cells.filter(cell => {
      const parent = cell.getBoundingClientRect();
      return Array.from(cell.children).some(child => {
        const bounds = child.getBoundingClientRect();
        return bounds.top < parent.top - 1 || bounds.bottom > parent.bottom + 1 || child.scrollHeight > child.clientHeight + 1 || child.scrollWidth > child.clientWidth + 1;
      });
    }).map(cell => cell.textContent.trim()));
    assert.deepEqual(clipped, [], `Chart text must remain visible: ${selector}`);
  }
  async function onScreen(locator) {
    await page.evaluate(() => scrollTo(0, 0));
    const box = await locator.boundingBox();
    if (box.y + box.height > 768) {
      await page.screenshot({ path: path.join(output, 'compact-chart-fit-failure.png') });
      console.log(await page.locator('#panel-divisional .divisional-subtabs, #subtab-D1-control').evaluateAll(nodes => nodes.map(node => ({ text: node.textContent.trim().slice(0, 40), top: node.getBoundingClientRect().top, height: node.getBoundingClientRect().height, width: node.getBoundingClientRect().width, padding: getComputedStyle(node).padding, fontSize: getComputedStyle(node).fontSize, minWidth: getComputedStyle(node).minWidth }))));
    }
    assert.ok(box.y >= 0 && box.y + box.height <= 768, `Chart must fit the laptop viewport: ${JSON.stringify(box)}`);
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
    for (const code of ['D1', 'D9', 'D10']) {
      await page.getByRole('button', { name: code, exact: true }).click();
      await onScreen(page.locator('.rasi-grid'));
      await unclipped('.rasi-cell, .rasi-center');
    }
    await page.getByRole('button', { name: 'D1', exact: true }).click();
    const chartPanel = await page.locator('.dashboard .chart-panel').boundingBox();
    const dashaPanel = await page.locator('.dashboard .dasha-card').boundingBox();
    const positionsPanel = await page.locator('.dashboard .planets-panel').boundingBox();
    assert.ok(dashaPanel.y >= chartPanel.y + chartPanel.height, 'Current Dasha belongs below the chart');
    assert.ok(positionsPanel.x >= chartPanel.x + chartPanel.width, 'Planetary Positions belongs to the right of the chart');
    assert.ok(Math.abs(positionsPanel.y - chartPanel.y) < 1, 'Chart and Planetary Positions align at the top');
    assert.equal(await page.locator('.dashboard .identity-card, .dashboard .panchanga-card').count(), 0);
    assert.equal(await page.locator('.dashboard .planet-table tbody tr').count(), 9);
    assert.equal(await page.locator('.dashboard .planet-table thead th').count(), 8);
    assert.ok(await page.locator('.dashboard .planets-panel .table-scroll').evaluate(node => node.scrollWidth <= node.clientWidth + 1), 'All table columns fit the laptop panel');
    for (const selector of ['.kendra-card', '.trikona-card']) {
      const lordCard = page.locator(`.dashboard ${selector}`);
      const bounds = await lordCard.boundingBox();
      assert.ok(bounds.x >= dashaPanel.x + dashaPanel.width, 'Lord cards belong to the right of Current Dasha');
      assert.ok(Math.abs(bounds.y - dashaPanel.y) < 1, 'Separate lord cards align with Current Dasha');
      assert.equal(await lordCard.locator('li').count(), 3);
    }
    const kendraPanel = await page.locator('.dashboard .kendra-card').boundingBox();
    const trikonaPanel = await page.locator('.dashboard .trikona-card').boundingBox();
    assert.ok(trikonaPanel.x >= kendraPanel.x + kendraPanel.width, 'Kendra and Trikona have separate cards');
    await page.screenshot({ path: path.join(output, 'birth-lords-beside-dasha.png'), fullPage: true });
    await page.screenshot({ path: path.join(output, 'compact-birth-laptop.png') });
    await page.locator('.dashboard .dasha-card').getByRole('button', { name: 'Explore', exact: true }).click();
    assert.ok(await page.locator('#panel-dasha').isVisible());
    await nav('Birth chart');
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      const chart = await page.locator('.dashboard .chart-panel').boundingBox();
      const dasha = await page.locator('.dashboard .dasha-card').boundingBox();
      const positions = await page.locator('.dashboard .planets-panel').boundingBox();
      assert.ok(dasha.y >= chart.y + chart.height);
      assert.ok(positions.y >= dasha.y + dasha.height, 'Mobile order is chart, Current Dasha, then Planetary Positions');
      const kendra = await page.locator('.dashboard .kendra-card').boundingBox();
      const trikona = await page.locator('.dashboard .trikona-card').boundingBox();
      assert.ok(kendra.y >= positions.y + positions.height);
      assert.ok(trikona.y >= kendra.y + kendra.height, 'Separate lord cards stack on mobile');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      assert.equal(await page.locator('.planet-table tbody tr').count(), 9);
      await unclipped('.rasi-cell, .rasi-center');
    }
    await page.screenshot({ path: path.join(output, 'birth-layout-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1366, height: 768 });
    console.log('PASS: Dasha below chart; separate Kendra/Trikona cards aligned on its right; all 9 planets and 8 columns; mobile order; Explore navigation');
    console.log('PASS: D1/D9/D10 fit a 1366×768 laptop without scrolling');

    const codes = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D16', 'D20', 'D24', 'D27', 'D30', 'D40', 'D45', 'D60', 'D81', 'D108', 'D144'];
    await nav('Divisional charts');
    for (const width of [1366, 390, 320]) {
      await page.setViewportSize({ width, height: width > 780 ? 768 : 900 });
      for (const code of codes) {
        await page.getByRole('tab', { name: code, exact: true }).click();
        const panel = '#panel-divisional .subtab-panel:visible';
        assert.equal(await page.locator(`${panel} .planet-degree`).count(), 9);
        const layout = page.locator(`${panel} .divisional-layout`);
        assert.equal(await layout.getAttribute('class'), code === 'D1' ? 'divisional-layout' : 'divisional-layout with-amsa');
        if (code !== 'D1') {
          assert.equal(await layout.locator('.amsa-ruler-table tbody tr').count(), 10);
          const chartBox = await layout.locator('.chart-grid').boundingBox();
          const rulerBox = await layout.locator('.amsa-rulers').boundingBox();
          if (width === 1366) {
            assert.ok(rulerBox.x >= chartBox.x + chartBox.width, `${code} amsa rulers must be beside the chart on the right`);
            assert.ok(Math.abs(rulerBox.y - chartBox.y) < 2, `${code} chart and ruler table must align at the top`);
          } else assert.ok(rulerBox.y >= chartBox.y + chartBox.height, `${code} rulers stack below the chart on mobile`);
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        try { await unclipped(`${panel} .chart-cell:not(.blank), ${panel} .chart-center`); }
        catch (error) { console.error(`Clipping in ${code} at ${width}px`); throw error; }
        if (width === 1366 && ['D1', 'D12', 'D144'].includes(code)) await onScreen(page.locator(`${panel} .chart-grid`));
      }
    }
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.getByRole('tab', { name: 'D12', exact: true }).click();
    await page.evaluate(() => scrollTo(0, 0));
    await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(output, 'compact-divisional-laptop.png') });
    await page.locator('#panel-divisional .subtab-panel:visible').screenshot({ path: path.join(output, 'divisional-amsa-beside-chart.png') });
    await page.getByRole('tab', { name: 'Bhava Chalit', exact: true }).click();
    assert.equal(await page.locator('#panel-divisional .subtab-panel:visible .with-amsa').count(), 0);
    assert.equal(await page.locator('#panel-divisional .subtab-panel:visible .amsa-rulers').count(), 0);
    console.log('PASS: all 23 divisions retain all nine degrees and unclipped cells/centers at 320–1366px');

    await nav('Bhrigu Chakra Paddhati');
    await onScreen(page.locator('#panel-bcp .bhrigu-natal-grid'));
    await unclipped('#panel-bcp .bhrigu-natal-cell, #panel-bcp .bhrigu-natal-center');
    await nav('Dasha');
    await onScreen(page.locator('.vimshottari-chart .rasi-grid'));
    await unclipped('.vimshottari-chart .rasi-cell, .vimshottari-chart .rasi-center');
    await nav('Ashtakavarga');
    for (const width of [1366, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert.equal(await page.locator('#panel-ashtakavarga .mini-chart-grid').count(), 9);
      await unclipped('#panel-ashtakavarga .mini-chart-cell:not(.blank)');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.screenshot({ path: path.join(output, 'compact-ashtakavarga-laptop.png') });
    assert.deepEqual(errors, []);
    console.log('PASS: compact Bhrigu/dasha charts fit the laptop, and Ashtakavarga stays readable on mobile');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
