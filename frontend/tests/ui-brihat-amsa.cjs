const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve(process.env.ASTRO_SCREENSHOTS || 'test-results');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  // The chosen chart's civil period boundaries must work in another timezone.
  const page = await browser.newPage({ viewport: { width: 1536, height: 1100 }, timezoneId: 'America/New_York' });
  page.setDefaultTimeout(60000);
  const errors = [], external = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== new URL(origin).origin) {
      external.push(route.request().url()); return route.abort();
    }
    return route.continue();
  });
  const nav = label => page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: label, exact: true }).click();
  const overflow = async () => assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  const afterBoundary = value => new Date(Math.ceil(Date.parse(`${value.slice(0, 23)}Z`) / 1000) * 1000).toISOString().slice(0, 19);
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
    const response = await posted;
    assert.equal(response.status(), 200);
    const html = await response.text();
    const state = JSON.parse(html.match(/<script id="astro-state" type="application\/json">([\s\S]*?)<\/script>/)[1]);
    await page.locator('.rasi-grid').waitFor();
    await nav('Brihat Jataka');
    const bjnav = page.getByRole('navigation', { name: 'Brihat Jataka views' });
    assert.equal(await bjnav.getByRole('button').count(), 6);
    assert.equal(await bjnav.getByRole('button', { name: 'Overview' }).count(), 0);
    assert.equal(await bjnav.getByRole('button', { name: 'Complete book' }).count(), 0);
    assert.ok(await page.locator('.bj-strength-graphs').isVisible());
    const marks = page.locator('[data-category="sthana"] .bj-strength-row');
    const geometry = await marks.evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().toJSON()));
    assert.ok(geometry.every(rect => rect.y === geometry[0].y));
    assert.ok(geometry.every((rect, i) => !i || rect.x > geometry[i - 1].x));
    assert.equal(await page.locator('[data-category="sthana"] .bj-strength-scale').innerText(), '5\n4\n3\n2\n1\n0');
    await bjnav.getByRole('button', { name: 'Predictions', exact: false }).click();
    assert.equal(await page.locator('.bj-prediction-reading').count(), state.brihat_jataka.predictions.readings.length);
    const date = page.getByLabel('Reading date & time');
    const fillDate = value => date.fill(value.replace(/:00$/, ''));
    await fillDate('1998-09-04T00:02:59');
    assert.match(await page.locator('.bj-period-empty').innerText(), /outside/);
    await fillDate('1998-09-04T00:03:00');
    assert.equal(await page.locator('[data-period-kind="Main period"]').getAttribute('data-lord'), 'Lagna');
    assert.match(await page.locator('[data-period-kind="Main period"]').innerText(), /Venus rules your rising sign/);
    const second = state.brihat_jataka.dasha.periods[1];
    await fillDate(afterBoundary(second.start));
    assert.equal(await page.locator('[data-period-kind="Main period"]').getAttribute('data-lord'), second.lord);
    await fillDate('2200-01-01T00:00:00');
    assert.match(await page.locator('.bj-period-empty').innerText(), /outside/);
    assert.equal(await page.locator('[data-period-kind="Main period"]').count(), 0);
    await fillDate('1998-09-04T00:03:00');
    const filters = page.getByRole('navigation', { name: 'Prediction categories' });
    await filters.getByRole('button', { name: 'Personality & habits', exact: true }).click();
    assert.equal(await page.locator('.bj-prediction-reading').count(), 7);
    const sun = page.locator('[data-reading-id="sign-sun"]');
    assert.match(await sun.innerText(), /Sun in Leo/);
    await sun.locator('summary').click();
    assert.match(await sun.innerText(), /D1 Sun in Leo/);
    assert.equal(await page.locator('.bj-workspace .bj-source-link').count(), 0);
    assert.match(await sun.innerText(), /Rule applied/);
    assert.ok(!(await page.locator('.bj-workspace').innerText()).includes('XVIII.'));
    await page.getByRole('button', { name: 'View full dasha timeline', exact: false }).click();
    const methods = page.getByRole('navigation', { name: 'Brihat dasha methods' });
    assert.equal(await methods.getByRole('button').count(), 2);
    const calc = page.getByRole('region', { name: 'Ayurdaya calculation steps' });
    await calc.locator('tbody tr').first().getByText('Show steps', { exact: true }).click();
    assert.match(await calc.locator('tbody tr').first().innerText(), /Birth position: Leo/);
    assert.match(await calc.locator('tbody tr').first().innerText(), /Amsa base:/);
    await methods.getByRole('button', { name: 'Naisargika dasha', exact: false }).click();
    const natural = page.getByRole('region', { name: 'Natural dashas' });
    assert.equal(await natural.locator('tbody tr').count(), 7);
    assert.deepEqual(await natural.locator('tbody tr td:first-child').allTextContents(), ['Moon', 'Mars', 'Mercury', 'Venus', 'Jupiter', 'Sun', 'Saturn']);
    assert.deepEqual(await natural.locator('tbody tr td:nth-child(2)').allTextContents(), ['0–1', '1–3', '3–12', '12–32', '32–50', '50–70', '70–120']);
    await fillDate('1998-09-04T00:03:00');
    assert.equal(await page.locator('[data-period-kind="Main period"]').getAttribute('data-lord'), 'Moon');
    await fillDate(afterBoundary(state.brihat_jataka.natural_dasha[1].start));
    assert.equal(await page.locator('[data-period-kind="Main period"]').getAttribute('data-lord'), 'Mars');
    await page.locator('.bj-workspace').screenshot({ path: path.join(output, 'brihat-naisargika-desktop.png') });
    await methods.getByRole('button', { name: 'Ayurdaya dasha', exact: false }).click();
    await page.locator('.bj-workspace').screenshot({ path: path.join(output, 'brihat-ayurdaya-desktop.png') });
    await bjnav.getByRole('button', { name: 'Predictions', exact: false }).click();
    await filters.getByRole('button', { name: 'Work & money', exact: true }).click();
    assert.equal(await page.locator('.bj-prediction-reading').count(), 3);
    await filters.getByRole('button', { name: 'Planet support', exact: true }).click();
    assert.equal(await page.locator('.bj-prediction-reading').count(), 7);
    await filters.getByRole('button', { name: 'All readings', exact: true }).click();
    await page.locator('.bj-workspace').screenshot({ path: path.join(output, 'brihat-predictions-desktop.png') });
    await bjnav.getByRole('button', { name: 'Ashtakavarga', exact: false }).click();
    assert.equal(await page.locator('.bj-ashtaka-charts figure').count(), 8);
    assert.equal(await page.locator('.bj-ashtaka-charts .mini-chart-cell:not(.blank)').count(), 96);
    const signNames = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
    for (const row of state.brihat_jataka.ashtakavarga) {
      const tile = page.locator(`[data-ashtaka-planet="${row.planet}"]`);
      for (let i = 0; i < 12; i++) assert.equal(Number(await tile.locator(`[data-sign="${signNames[i]}"]`).getAttribute('data-bindus')), row.scores[i]);
    }
    const totals = await page.locator('[data-ashtaka-planet="SAV"] [data-bindus]').evaluateAll(nodes => nodes.map(node => Number(node.dataset.bindus)));
    assert.equal(totals.reduce((sum, value) => sum + value, 0), 337);
    assert.equal(await page.locator('.bj-ashtaka-charts .mini-chart-cell.natal-occupied').count(), 0);
    await page.locator('.bj-ashtaka-charts').screenshot({ path: path.join(output, 'brihat-ashtakavarga-charts-desktop.png') });
    for (const width of [320, 390, 768]) { await page.setViewportSize({ width, height: 1000 }); await overflow(); }
    await page.setViewportSize({ width: 1536, height: 1100 });
    await bjnav.getByRole('button', { name: 'Dashas', exact: false }).click();
    await page.getByRole('combobox', { name: 'Year method' }).selectOption('pinda');
    await page.getByRole('combobox', { name: 'Starting point' }).selectOption('Sun');
    await bjnav.getByRole('button', { name: 'Predictions', exact: false }).click();
    assert.match(await page.locator('.bj-prediction-timing').innerText(), /settings have changed/);
    await bjnav.getByRole('button', { name: 'Dashas', exact: false }).click();
    await page.getByRole('button', { name: 'Calculate worksheet', exact: true }).click();
    await page.getByRole('heading', { name: 'Pindayurdaya · Sun first' }).waitFor();
    await bjnav.getByRole('button', { name: 'Predictions', exact: false }).click();
    // The tab remounts with today's date. Return to the first period explicitly.
    await fillDate('1998-09-04T00:03:00');
    assert.equal(await page.locator('[data-period-kind="Main period"]').getAttribute('data-lord'), 'Sun');
    assert.match(await page.locator('.bj-prediction-timing').innerText(), /Pinda · based on distance from exaltation/);
    for (const width of [320, 390, 768, 1536]) {
      await page.setViewportSize({ width, height: 1000 }); await overflow();

    }
    await nav('Divisional charts');
    for (const code of ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D16', 'D20', 'D24', 'D27', 'D30', 'D40', 'D45', 'D60', 'D81', 'D108', 'D144']) {
      await page.locator('#panel-divisional').getByRole('tab', { name: code, exact: true }).click();
      const selected = page.locator('#panel-divisional .subtab-panel:visible');
      assert.equal(await selected.locator('.amsa-ruler-table tbody tr').count(), 10);
      assert.equal(await selected.locator('.amsa-ruler-table thead th').count(), 5);
      assert.match(await selected.locator('.amsa-ruler-table tbody tr').first().innerText(), /Ascendant/);
      assert.equal(await selected.locator('.planet-degree').count(), 9);
      if (['D81', 'D108', 'D144'].includes(code)) assert.match(await selected.innerText(), /Component rules/);
      if (['D5', 'D6', 'D8', 'D11'].includes(code)) assert.match(await selected.innerText(), /Not confirmed/);
      await overflow();
    }
    await page.locator('#panel-divisional').getByRole('tab', { name: 'D12', exact: true }).click();
    const d12 = page.locator('#panel-divisional .subtab-panel:visible');
    assert.equal(await d12.locator('[data-body="Sun"] .amsa-deity').innerText(), 'Yama');
    await d12.screenshot({ path: path.join(output, 'd12-amsa-rulers-desktop.png') });
    for (const width of [320, 390, 768]) {
      await page.setViewportSize({ width, height: 1000 }); await overflow();
      await page.locator('#panel-divisional').getByRole('tab', { name: 'D144', exact: true }).click();
      await overflow();
    }
    assert.deepEqual(errors, []); assert.deepEqual(external, []);
    console.log('PASS: six Brihat tabs, vertical plot geometry, sourced predictions, date boundaries, dasha recalculation, plain rules, calculation steps, Naisargika and Ayurdaya, all 96 Ashtakavarga cells, all 23 amsa tables, mobile widths and offline operation');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
