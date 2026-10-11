const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve(process.env.ASTRO_SCREENSHOTS || 'test-results');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1536, height: 1100 } });
  const errors = [], external = [];
  await context.route('**/*', route => {
    if (new URL(route.request().url()).origin !== origin) { external.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(60000);
  page.on('pageerror', error => errors.push(error.message));
  const nav = label => page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: label, exact: true }).click();
  const shot = name => page.screenshot({ path: path.join(output, `${name}.png`), fullPage: true });
  const vedic = () => page.locator('.vedic-aspect-table tbody').evaluate(body => Array.from(body.rows, row => ({
    planet: row.dataset.planet,
    sourceSign: row.cells[1].textContent.trim(),
    targets: Array.from(row.cells[2].querySelectorAll('[data-target]'), e => [e.dataset.target, Number(e.dataset.aspect)]),
    signs: Array.from(row.cells[3].querySelectorAll('[data-sign]'), e => [e.dataset.sign, Number(e.dataset.aspect)]),
  })));
  const western = () => page.locator('.western-aspect-table [data-target]');
  async function fillBirth(target) {
    await target.locator('#name').fill('Manikanta Kavala');
    await target.locator('#birth_date').fill('04/09/1998');
    await target.locator('#birth_hour').selectOption('12');
    await target.locator('#birth_minute').selectOption('3');
    await target.locator('#birth_meridiem').selectOption('AM');
    await target.getByText('Advanced settings', { exact: true }).click();
    await target.locator('#manual_latitude').fill('17.00517');
    await target.locator('#manual_longitude').fill('81.77784');
    await target.locator('#manual_utc_offset_hours').fill('5.5');
  }
  try {
    await page.goto(origin);
    await page.locator('.app-shell').waitFor();
    await fillBirth(page);
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('.rasi-grid').waitFor();
    await nav('Aspects');
    const panel = page.locator('.planetary-aspects');
    await panel.waitFor();
    assert.deepEqual(await page.locator('.vedic-aspect-table thead th').allTextContents(), ['Planet', 'Sign occupied', 'Aspected planets', 'Aspected signs']);
    const actual = await vedic();
    assert.equal(actual.length, 9);
    assert.deepEqual(actual.map(row => row.sourceSign), ['Leo', 'Capricorn', 'Cancer', 'Cancer', 'Pisces', 'Leo', 'Aries', 'Leo', 'Aquarius']);
    assert.equal(await page.locator('.vedic-aspect-table tr[data-planet="Moon"] [data-target="Mars"] small').innerText(), 'Cancer');
    const vedicMars = page.locator('.vedic-aspect-table tr[data-planet="Moon"] [data-target="Mars"]');
    const nameBox = await vedicMars.locator(':scope > span').boundingBox();
    const signBox = await vedicMars.locator('small').boundingBox();
    assert.ok(signBox.y >= nameBox.y + nameBox.height, 'Target signs remain on their own readable line');
    assert.deepEqual(actual.map(row => row.targets), [
      [['Ketu', 7]], [['Mars', 7], ['Mercury', 7]], [['Moon', 7], ['Ketu', 8]],
      [['Moon', 7]], [['Mars', 5], ['Mercury', 5]], [['Ketu', 7]], [['Moon', 10]], [], [],
    ]);
    assert.deepEqual(actual[4].signs, [['Cancer', 5], ['Virgo', 7], ['Scorpio', 9]]);
    assert.deepEqual(actual[2].signs, [['Libra', 4], ['Capricorn', 7], ['Aquarius', 8]]);
    assert.equal(await panel.locator('.current-period').count(), 0);
    const backgrounds = await page.locator('.vedic-aspect-table tbody tr').evaluateAll(rows => rows.map(row => getComputedStyle(row).backgroundColor));
    assert.deepEqual([...new Set(backgrounds)], ['rgba(0, 0, 0, 0)']);
    for (const row of actual) assert.ok(await page.locator(`.vedic-aspect-table tr[data-planet="${row.planet}"] .planet-color-${row.planet.toLowerCase()}`).first().isVisible());
    await shot('aspects-vedic-desktop');
    await panel.screenshot({ path: path.join(output, 'aspects-vedic-table.png') });
    console.log('PASS: full planet names, real natal sign aspects, empty aspected signs, colors and uniform rows');

    const tabs = page.getByRole('tablist', { name: 'Aspect methods' });
    await tabs.getByRole('tab', { name: 'Vedic Aspects', exact: true }).focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await tabs.getByRole('tab', { name: 'Western Aspects', exact: true }).getAttribute('aria-selected'), 'true');
    assert.ok(await page.locator('#aspect-view-western').isVisible());
    assert.deepEqual(await page.locator('.western-aspect-table thead th').allTextContents(), ['Planet', 'Sign occupied', 'Aspected planets', 'Aspected signs']);
    const orb = page.getByLabel('Orb tolerance (°)', { exact: true });
    assert.equal(await orb.inputValue(), '6');
    const count6 = await western().count();
    assert.ok(count6 > 2);
    const moonMars = page.locator('.western-aspect-table tr[data-planet="Moon"] [data-target="Mars"]');
    assert.ok((await moonMars.innerText()).includes('Opposition [180°]'));
    assert.equal(await moonMars.locator('small').first().innerText(), 'Cancer');
    assert.ok(Math.abs(Number(await moonMars.getAttribute('data-orb')) - 3.7111) < 0.01);
    await shot('aspects-western-desktop');
    await orb.fill('0');
    assert.equal(await western().count(), 2); // Exact Rahu/Ketu opposition in both directions.
    await orb.fill('10');
    assert.ok(await western().count() >= count6);
    await orb.fill('11');
    assert.equal(await orb.getAttribute('aria-invalid'), 'true');
    assert.equal(await western().count(), count6);
    await orb.fill('');
    assert.ok(await page.getByRole('status').isVisible());
    await orb.fill('4');
    assert.equal(await page.locator('.western-aspect-table tr[data-planet="Saturn"] [data-target="Mars"]').count(), 0);
    assert.equal(await orb.getAttribute('aria-invalid'), 'false');
    await orb.fill('6');
    await tabs.getByRole('tab', { name: 'Western Aspects', exact: true }).focus();
    await page.keyboard.press('Home');
    assert.ok(await page.locator('#aspect-view-vedic').isVisible());
    console.log('PASS: working Western angular aspects, orb filtering and validation, keyboard tab navigation');

    for (const width of [1536, 1280, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1050 });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Overflow at ${width}`);
      if (width === 390) await shot('aspects-vedic-mobile');
      await tabs.getByRole('tab', { name: 'Western Aspects', exact: true }).click();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Western overflow at ${width}`);
      if (width === 390) await shot('aspects-western-mobile');
      await tabs.getByRole('tab', { name: 'Vedic Aspects', exact: true }).click();
    }
    console.log('PASS: both aspect tables at 320–1536px');

    await page.setViewportSize({ width: 1536, height: 1100 });
    await page.locator('.ribbon-edit').click();
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#house_system').selectOption('placidus');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('.rasi-grid').waitFor();
    await nav('Aspects');
    assert.deepEqual(await vedic(), actual);
    await page.locator('.ribbon-edit').click();
    await page.locator('#birth_date').fill('01/01/2001');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('.rasi-grid').waitFor();
    await nav('Aspects');
    assert.notDeepEqual(await vedic(), actual);
    console.log('PASS: sign aspects stay independent of house settings and recalculate for changed birth details');

    const nativeContext = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1280, height: 1000 } });
    const nativePage = await nativeContext.newPage();
    await nativePage.goto(origin);
    await fillBirth(nativePage);
    await nativePage.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await nativePage.locator('.tab-bar label[for="tab-aspects"]').click();
    assert.ok(await nativePage.locator('.native-vedic-aspects').isVisible());
    assert.equal(await nativePage.locator('.native-vedic-aspects tbody tr').count(), 9);
    assert.equal(await nativePage.locator('.native-vedic-aspects thead th').count(), 4);
    await nativePage.locator('label[for="native-aspect-western"]').click();
    assert.ok(await nativePage.locator('.native-western-aspects').isVisible());
    assert.ok(!(await nativePage.locator('.native-vedic-aspects').isVisible()));
    assert.equal(await nativePage.locator('.native-western-aspects tbody tr').count(), 9);
    assert.equal(await nativePage.locator('.native-western-aspects thead th').count(), 4);
    await nativeContext.close();
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    console.log('PASS: native HTML fallback, offline runtime and no browser errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
