const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve('test-results');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1536, height: 1000 }, timezoneId: 'America/Los_Angeles' });
  const page = await context.newPage();
  const errors = [];
  const external = [];
  page.on('pageerror', e => errors.push(e.message));
  page.setDefaultTimeout(60000);
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== origin) { external.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  const panel = page.locator('#panel-jaimini');
  const tab = name => panel.getByRole('tab', { name, exact: true });
  const overflow = async () => assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'No page overflow');
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
    await page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: 'Jaimini North', exact: true }).click();
    await panel.getByRole('table', { name: 'Chara Karakas', exact: true }).waitFor();
    assert.equal(await panel.getByRole('table', { name: 'Chara Karakas', exact: true }).locator('tbody tr').count(), 7);
    await panel.locator('.jaimini-dasha-columns[aria-busy="false"]').waitFor();
    await page.screenshot({ path: path.join(output, 'jaimini-dashboard-desktop.png'), fullPage: true });
    await panel.getByRole('button', { name: '8 karakas', exact: true }).click();
    const karakas = panel.getByRole('table', { name: 'Chara Karakas', exact: true });
    assert.equal(await karakas.locator('tbody tr').count(), 8);
    assert.ok((await karakas.innerText()).includes('Rahu'));
    await panel.getByRole('button', { name: 'Karakamsha', exact: true }).click();
    assert.equal(await panel.locator('.rasi-cell.is-ascendant').count(), 1);
    assert.ok((await panel.locator('.chart-legend').innerText()).includes('Atmakaraka'));
    await panel.getByRole('button', { name: 'Swamsha', exact: true }).click();
    await panel.getByRole('button', { name: '7 karakas', exact: true }).click();
    for (const name of ['Rashi Aspects', 'Arudha Padas', 'Upapada', 'Argala', 'Yogas', 'Predictions', 'Advanced']) {
      await tab(name).click(); await overflow();
      assert.ok((await panel.innerText()).includes(name === 'Advanced' ? 'Special Lagnas' : name === 'Rashi Aspects' ? 'Rashi Drishti' : name === 'Predictions' ? 'plain language' : name === 'Yogas' ? 'Yogada' : name));
    }
    await tab('Rashi Aspects').click();
    assert.equal(await panel.getByRole('table', { name: 'Jaimini sign aspects', exact: true }).locator('tbody tr').count(), 9);
    await tab('Arudha Padas').click();
    assert.equal(await panel.getByRole('table', { name: 'Arudha Padas', exact: true }).locator('tbody tr').count(), 12);
    await tab('Argala').click();
    for (const sign of ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']) {
      await panel.getByLabel('Argala target sign').selectOption(sign);
      assert.equal(await panel.getByRole('table').locator('tbody tr').count(), 4);
    }
    await tab('Dashas').click();
    await panel.getByLabel('Jaimini dasha levels').selectOption('5');
    await panel.locator('.jaimini-dasha-columns[aria-busy="false"]').waitFor();
    assert.equal(await panel.locator('.jaimini-dasha-column').count(), 5);
    assert.equal(await panel.locator('.jaimini-dasha-column:last-child tbody tr').count(), 12);
    for (const code of ['narayana', 'kendradi', 'sudasha', 'drig', 'shoola', 'niryana', 'navamsa', 'sthira', 'brahma', 'mandooka', 'chara']) {
      await panel.getByLabel('Jaimini North dasha method').selectOption(code);
      await page.waitForFunction(() => !document.querySelector('#panel-jaimini .jaimini-dasha-columns[aria-busy="true"]') && !document.querySelector('#panel-jaimini .jaimini-dasha-controls [role="status"]')?.textContent.includes('Calculating'));
      await overflow();
    }
    await panel.getByLabel('Jaimini dasha date and time').fill('1998-09-04T00:03');
    await panel.locator('.jaimini-dasha-columns[aria-busy="false"]').waitFor();
    const first = await panel.locator('.jaimini-dasha-column:first-child .is-selected').innerText();
    assert.ok(first.includes('04/09/98'), 'Birth boundary uses birth-place time despite US browser timezone');
    await page.screenshot({ path: path.join(output, 'jaimini-dashas-desktop.png'), fullPage: true });
    await tab('Charts & Karakas').click();
    await panel.getByRole('button', { name: 'D1', exact: true }).click();
    for (const width of [1366, 390, 320]) {
      await page.setViewportSize({ width, height: 768 }); await overflow();
      for (const chart of ['D1', 'D9', 'Karakamsha', 'Swamsha']) {
        await panel.getByRole('button', { name: chart, exact: true }).click();
        const clipped = await panel.locator('.rasi-cell, .rasi-center').evaluateAll(cells => cells.filter(cell => [...cell.children].some(child => {
          const c = child.getBoundingClientRect(), b = cell.getBoundingClientRect();
          return c.bottom > b.bottom + 1 || c.right > b.right + 1 || child.scrollWidth > child.clientWidth + 1 || child.scrollHeight > child.clientHeight + 1;
        })).map(cell => cell.textContent));
        assert.deepEqual(clipped, [], `Chart text fits at ${width}px (${chart})`);
      }
      if (width === 1366) {
        await page.evaluate(() => scrollTo(0, 0));
        const box = await panel.locator('.rasi-grid').boundingBox();
        assert.ok(box.y + box.height < 768, 'Whole Jaimini chart visible on laptop');
      }
      if (width === 390) await page.screenshot({ path: path.join(output, 'jaimini-dashboard-mobile.png'), fullPage: true });
      for (const name of ['Rashi Aspects', 'Arudha Padas', 'Dashas', 'Advanced']) { await tab(name).click(); await overflow(); }
      await tab('Charts & Karakas').click();
    }
    assert.deepEqual(errors, []); assert.deepEqual(external, []);
    console.log('PASS: all nine Jaimini sections, 7/8 karakas, four charts, all 11 dasha methods, Prana, birth boundary, mobile/laptop fit and offline requests');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
