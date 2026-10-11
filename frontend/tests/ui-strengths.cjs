const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve('test-results');
fs.mkdirSync(output, { recursive: true });
const colors = { Sun: 'rgb(248, 163, 67)', Moon: 'rgb(222, 219, 233)', Mars: 'rgb(219, 128, 118)', Mercury: 'rgb(127, 200, 156)', Jupiter: 'rgb(237, 203, 114)', Venus: 'rgb(228, 144, 193)', Saturn: 'rgb(149, 181, 234)' };
const checks = {
  sthana: row => row.sthana_checks.map(check => check.supported), dig: row => [row.dig],
  chesta: row => [row.chesta_supported], kala: row => [row.kala, row.paksha],
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1536, height: 1100 }, timezoneId: 'America/Los_Angeles' });
  page.setDefaultTimeout(60000);
  const errors = [], external = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== origin) { external.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  const nav = label => page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: label, exact: true }).click();
  const noOverflow = async () => assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  async function generate() {
    const response = page.waitForResponse(r => r.url() === `${origin}/` && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    const result = await response;
    assert.equal(result.status(), 200);
    const html = await result.text();
    const state = JSON.parse(html.match(/<script id="astro-state" type="application\/json">([\s\S]*?)<\/script>/)[1]);
    await page.waitForFunction(expected => document.querySelector('#panel-panchanga .birth-hora-row strong')?.textContent === expected, `${state.panchanga.hora.lord} hora`);
    assert.ok(html.includes(`data-hora-start datetime="${state.panchanga.hora.start}"`));
    return state;
  }
  async function validateGraphs(state) {
    assert.equal(await page.locator('.bj-strength-graph').count(), 4);
    const summaryRows = page.locator('.bj-support-table tbody tr');
    assert.equal(await summaryRows.count(), 7);
    for (const [category, getChecks] of Object.entries(checks)) {
      const graph = page.locator(`.bj-strength-graph[data-category="${category}"]`);
      for (let index = 0; index < state.brihat_jataka.strengths.length; index++) {
        const row = state.brihat_jataka.strengths[index], conditions = getChecks(row);
        const count = conditions.filter(Boolean).length;
        const button = graph.locator(`.bj-strength-row[data-planet="${row.planet}"]`);
        assert.equal(Number(await button.getAttribute('data-value')), count);
        assert.equal(Number(await button.getAttribute('data-maximum')), conditions.length);
        assert.equal(await button.locator('.bj-strength-planet').innerText(), row.planet);
        assert.ok((await button.getAttribute('aria-label')).includes(`${count} of ${conditions.length}`));
        if (count) {
          assert.equal(await button.locator('.bj-strength-zero').count(), 0);
          const bar = await button.locator('.bj-strength-bar').evaluate(node => ({ height: node.getBoundingClientRect().height, track: node.parentElement.getBoundingClientRect().height, color: getComputedStyle(node).backgroundColor }));
          assert.equal(bar.color, colors[row.planet]);
          assert.ok(Math.abs(bar.height / bar.track - count / conditions.length) < .002);
        } else {
          assert.equal(await button.locator('.bj-strength-bar').count(), 0);
          const marker = button.locator('.bj-strength-zero');
          assert.ok(await marker.isVisible());
          assert.equal(await marker.evaluate(node => getComputedStyle(node).borderTopColor), colors[row.planet]);
          const markerBox = await marker.boundingBox(), trackBox = await button.locator('.bj-strength-track').boundingBox();
          assert.ok(Math.abs(markerBox.y + markerBox.height / 2 - trackBox.y - trackBox.height) < 1);
        }
        const column = Object.keys(checks).indexOf(category);
        assert.equal(await summaryRows.nth(index).locator('td').nth(column).innerText(), `${count}/${conditions.length}`);
      }
    }
    await noOverflow();
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
    let state = await generate();
    assert.equal(state.panchanga.hora.lord, 'Mercury');
    await nav('Panchanga');
    const panchanga = page.locator('#panel-panchanga');
    assert.ok((await panchanga.innerText()).includes('Night hora 7 of 12 · Hora 19 of 24'));
    assert.ok((await panchanga.innerText()).includes('UTC+05:30'));
    assert.equal(await panchanga.locator('[data-hora-start]').getAttribute('datetime'), state.panchanga.hora.start);
    assert.ok((await panchanga.locator('[data-hora-start]').innerText()).includes('12:02:19 AM'));
    await panchanga.locator('summary').click();
    assert.ok((await panchanga.innerText()).includes('03 Sep 1998'));
    assert.ok((await panchanga.innerText()).includes('Jupiter'));
    await page.screenshot({ path: path.join(output, 'panchanga-birth-hora.png'), fullPage: true });
    for (const width of [390, 320]) { await page.setViewportSize({ width, height: 900 }); await noOverflow(); }
    await page.setViewportSize({ width: 1536, height: 1100 });
    await nav('Brihat Jataka');
    await validateGraphs(state);
    assert.ok((await page.locator('[data-category="dig"] figcaption').innerText()).includes('No planet meets'));
    await page.locator('[data-category="sthana"] [data-planet="Mars"]').focus();
    assert.ok((await page.locator('[data-category="sthana"] .bj-strength-description').innerText()).includes('Mars'));
    await page.locator('.bj-strength-panel').screenshot({ path: path.join(output, 'brihat-strengths-redesigned.png') });
    await page.screenshot({ path: path.join(output, 'brihat-strengths-desktop.png'), fullPage: true });
    for (const width of [1366, 768, 390, 320]) {
      await page.setViewportSize({ width, height: width > 780 ? 768 : 900 });
      await validateGraphs(state);
      const clipped = await page.locator('.bj-strength-planet').evaluateAll(labels => labels.filter(node => node.scrollWidth > node.clientWidth + 1).map(node => node.textContent));
      assert.deepEqual(clipped, [], 'Full planet names must fit');
    }
    await page.screenshot({ path: path.join(output, 'brihat-strengths-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1536, height: 1100 });
    await page.getByRole('button', { name: 'Edit birth details', exact: true }).click();
    await page.locator('#birth_hour').selectOption('8');
    await page.locator('#birth_minute').selectOption('0');
    state = await generate();
    assert.equal(state.panchanga.hora.lord, 'Moon');
    assert.equal(state.panchanga.hora.phase, 'Day');
    await nav('Brihat Jataka');
    await validateGraphs(state);
    await page.locator('.bj-strength-details summary').click();
    assert.ok(await page.getByRole('region', { name: 'Classical planetary strengths', exact: true }).isVisible());
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    console.log('PASS: all four graphs, true zero markers, planetary colors, matching summary counts, keyboard details, full planet names and mobile layout');
    console.log('PASS: birth hora, previous sunrise, local times, native HTML fallback, and recalculation after editing birth inputs');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
