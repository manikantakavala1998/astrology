const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve('test-results');
fs.mkdirSync(output, { recursive: true });
const colors = { Sun: 'rgb(248, 163, 67)', Moon: 'rgb(222, 219, 233)', Mars: 'rgb(219, 128, 118)', Mercury: 'rgb(127, 200, 156)', Jupiter: 'rgb(237, 203, 114)', Venus: 'rgb(228, 144, 193)', Saturn: 'rgb(149, 181, 234)' };

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1536, height: 1100 }, timezoneId: 'America/Los_Angeles' });
  page.setDefaultTimeout(60000);
  const errors = [], external = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== origin) { external.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  const panel = page.locator('#panel-balas');
  async function noOverflow() { assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)); }
  async function generate() {
    const response = page.waitForResponse(r => r.url() === `${origin}/` && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    const result = await response;
    assert.equal(result.status(), 200);
    const html = await result.text();
    const state = JSON.parse(html.match(/<script id="astro-state" type="application\/json">([\s\S]*?)<\/script>/)[1]);
    await page.locator('.rasi-grid').waitFor();
    return state.balas;
  }
  async function graph(view) {
    const columns = await panel.locator('.strength-column').all();
    assert.equal(columns.length, view.rows.length);
    const zero = await panel.locator('.strength-zero').boundingBox();
    for (let index = 0; index < columns.length; index++) {
      const expected = view.rows[index], column = columns[index];
      assert.equal(Number(await column.getAttribute('data-value')), expected.value);
      assert.equal(await column.getAttribute('data-planet'), expected.planet);
      const metrics = await column.locator('.strength-bar').evaluate(node => ({ height: node.getBoundingClientRect().height, bottom: node.getBoundingClientRect().bottom, top: node.getBoundingClientRect().top, track: node.parentElement.getBoundingClientRect().height, color: getComputedStyle(node).backgroundColor }));
      assert.equal(metrics.color, colors[expected.planet]);
      assert.ok(Math.abs(metrics.height / metrics.track - Math.abs(expected.value) / (view.maximum - view.minimum)) < .002);
      assert.ok(Math.abs((expected.value < 0 ? metrics.top : metrics.bottom) - zero.y) < 2, 'Bars begin at zero, including negative aspects');
    }
    assert.equal(await panel.locator('.strength-required').count(), view.id === 'shadbala' ? 7 : 0);
    await noOverflow();
  }
  try {
    await page.goto(origin);
    await page.locator('#name').fill('Calculation check');
    await page.locator('#birth_date').fill('15/06/1990');
    await page.locator('#birth_hour').selectOption('8');
    await page.locator('#birth_minute').selectOption('30');
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#manual_latitude').fill('13.0827');
    await page.locator('#manual_longitude').fill('80.2707');
    await page.locator('#manual_utc_offset_hours').fill('5.5');
    let report = await generate();
    const navigation = page.getByRole('navigation', { name: 'Astrology sections' });
    const labels = await navigation.getByRole('button').allTextContents();
    const aspectIndex = labels.findIndex(label => label.includes('Aspects'));
    assert.ok(labels[aspectIndex + 1].includes('Strengths'));
    assert.equal(labels.filter(label => label.includes('Strengths')).length, 1);
    await navigation.getByRole('button', { name: 'Strengths', exact: true }).click();
    assert.equal(await panel.getByRole('tab').count(), 14);
    assert.ok(await panel.getByRole('tab', { name: 'Sthana Bala', exact: true }).getAttribute('aria-selected') === 'true');
    for (const view of report.views) {
      await panel.getByRole('tab', { name: view.name, exact: true }).click();
      await graph(view);
      await panel.getByLabel(view.id === 'bhava' ? 'House' : 'Planet', { exact: true }).selectOption(view.rows[0].key);
      assert.equal(await panel.locator('.bala-calculation-table tbody tr').count(), view.rows[0].details.length);
      assert.equal(await panel.getByLabel(view.id === 'bhava' ? 'House' : 'Planet', { exact: true }).locator('option').count(), view.rows.length);
      await panel.getByLabel(view.id === 'bhava' ? 'House' : 'Planet', { exact: true }).selectOption(view.rows[view.rows.length - 1].key);
      assert.ok((await panel.locator('.bala-calculation-table tfoot').innerText()).includes(view.rows[view.rows.length - 1].value.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })));
    }
    await panel.getByRole('tab', { name: 'Drik Bala', exact: true }).click();
    assert.ok(report.views.find(view => view.id === 'drik').minimum < 0);
    await page.screenshot({ path: path.join(output, 'balas-negative-aspects.png'), fullPage: true });
    const sthanaTab = panel.getByRole('tab', { name: 'Sthana Bala', exact: true });
    await sthanaTab.click(); await sthanaTab.focus(); await page.keyboard.press('ArrowDown');
    assert.equal(await panel.getByRole('tab', { name: 'Dig Bala', exact: true }).getAttribute('aria-selected'), 'true');
    await page.keyboard.press('End');
    assert.equal(await panel.getByRole('tab', { name: 'Kashta Phala', exact: true }).getAttribute('aria-selected'), 'true');
    await page.keyboard.press('Home');
    assert.equal(await panel.getByRole('tab', { name: 'Shadbala Total', exact: true }).getAttribute('aria-selected'), 'true');

    await page.getByRole('button', { name: 'Edit birth details', exact: true }).click();
    await page.locator('#name').fill('Manikanta Kavala');
    await page.locator('#birth_date').fill('04/09/1998');
    await page.locator('#birth_hour').selectOption('12');
    await page.locator('#birth_minute').selectOption('3');
    await page.locator('#birth_meridiem').selectOption('AM');
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#manual_latitude').fill('17.00517');
    await page.locator('#manual_longitude').fill('81.77784');
    report = await generate();
    if (!await panel.isVisible()) await navigation.getByRole('button', { name: 'Strengths', exact: true }).click();
    assert.equal(await panel.getByRole('tab', { name: 'Sthana Bala', exact: true }).getAttribute('aria-selected'), 'true');
    assert.ok((await panel.locator('.bala-calculation-table tfoot').innerText()).includes('194.59'));
    await graph(report.views.find(view => view.id === 'sthana'));
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, 'balas-separate-desktop.png'), fullPage: true });
    await panel.getByText('Full rules, division contributions & input values', { exact: true }).click();
    assert.equal(await panel.locator('.bala-contributions tbody tr').count(), 7);
    assert.ok((await panel.locator('.bala-inputs').innerText()).includes('1998-09-04T00:03'));
    await panel.getByText('Full rules, division contributions & input values', { exact: true }).click();
    for (const width of [1366, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      for (const view of report.views) {
        if (width > 900) await panel.getByRole('tab', { name: view.name, exact: true }).click();
        else await panel.getByLabel('Strength view', { exact: true }).selectOption(view.id);
        await graph(view);
        assert.ok((await panel.locator('.strength-graph').boundingBox()).height <= 280, 'Graphs stay compact');
      }
      if (width === 390) {
        await panel.getByLabel('Strength view', { exact: true }).selectOption('sthana');
        await page.screenshot({ path: path.join(output, 'balas-separate-mobile.png'), fullPage: true });
      }
    }
    assert.deepEqual(errors, []); assert.deepEqual(external, []);
    console.log('PASS: 14 separate views, actual arithmetic, negative aspects, all planet/house colors, keyboard navigation, recalculation and 320–1536px layouts');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
