const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const origin = process.env.ASTRO_TEST_URL || 'http://127.0.0.1:8765';
const output = path.resolve(process.env.ASTRO_SCREENSHOTS || 'test-results');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1536, height: 1100 } });
  page.setDefaultTimeout(60000);
  const errors = [];
  const external = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== new URL(origin).origin) {
      external.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  const shot = async name => page.screenshot({ path: path.join(output, `${name}.png`), fullPage: true });
  const nav = async label => page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: label }).click();
  const overflow = async () => {
    const size = await page.evaluate(() => ({ actual: document.documentElement.scrollWidth, expected: innerWidth }));
    assert.ok(size.actual <= size.expected + 1, `Page overflow: ${JSON.stringify(size)}`);
  };

  try {
    await page.goto(origin);
    await page.locator('.app-shell').waitFor();
    const birthDate = page.locator('#birth_date');
    assert.equal(await birthDate.getAttribute('type'), 'text');
    assert.equal(await birthDate.getAttribute('placeholder'), 'DD/MM/YYYY');
    await birthDate.fill('29/02/2023');
    assert.equal(await birthDate.evaluate(input => input.checkValidity()), false);
    await birthDate.fill('29022000');
    assert.equal(await birthDate.inputValue(), '29/02/2000');
    assert.equal(await birthDate.evaluate(input => input.checkValidity()), true);
    const birthCalendar = page.locator('.birth-date-calendar').first();
    assert.equal(await birthCalendar.inputValue(), '2000-02-29');
    await page.getByRole('button', { name: 'Choose date of birth from calendar', exact: true }).click();
    await page.keyboard.press('Escape');
    await birthCalendar.evaluate(input => { input.value = '1990-06-15'; input.dispatchEvent(new Event('change', { bubbles: true })); });
    assert.equal(await birthDate.inputValue(), '15/06/1990');
    await shot('birth-desktop');
    await page.locator('#name').fill('Design check');
    await page.locator('#birth_date').fill('15/06/1990');
    await page.locator('#birth_hour').selectOption('8');
    await page.locator('#birth_minute').selectOption('30');
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#manual_latitude').fill('13.0827');
    await page.locator('#manual_longitude').fill('80.2707');
    await page.locator('#manual_utc_offset_hours').fill('5.5');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('.rasi-grid').waitFor();
    assert.equal(await page.locator('.planet-table tbody tr').count(), 9);
    assert.equal(await page.locator('.planet-table thead th').count(), 8);
    assert.equal(await page.locator('.rasi-cell').count(), 12);
    for (const emoji of ['🔥', '🌍', '💨', '💧']) assert.ok((await page.locator('.rasi-grid').innerText()).includes(emoji));
    assert.ok((await page.locator('.rasi-cell.is-ascendant').innerText()).includes('Cancer'));
    await overflow();
    await shot('chart-desktop');
    await page.locator('.chart-panel').screenshot({ path: path.join(output, 'south-indian-chart.png') });
    await page.getByRole('button', { name: 'D9', exact: true }).click();
    assert.ok((await page.locator('.rasi-cell.is-ascendant').innerText()).includes('Virgo'));
    await page.getByRole('button', { name: 'D10', exact: true }).click();
    assert.ok((await page.locator('.rasi-cell.is-ascendant').innerText()).includes('Taurus'));
    await page.getByRole('button', { name: 'D1', exact: true }).click();
    console.log('PASS: birth input, calculation, all table fields, emojis, and D1/D9/D10');

    for (const [label, id] of [
      ['Dasha', 'dasha'], ['Aspects', 'aspects'], ['Divisional charts', 'divisional'],
      ['Ashtakavarga', 'ashtakavarga'], ['Shani', 'shani'], ['Doshas', 'dosha'],
      ['Strengths', 'balas'], ['Brihat Jataka', 'brihat-jataka'],
      ['Panchanga', 'panchanga'], ['Classic predictions', 'classic-predictions'],
      ['Yogas', 'yogas'], ['Tools', 'tools'],
    ]) {
      await nav(label);
      assert.ok(await page.locator(`#panel-${id}`).isVisible(), `${label} report must be accessible`);
      await overflow();
    }
    console.log('PASS: every existing analysis and pending section is accessible');

    assert.equal(await page.getByRole('button', { name: 'Bhrigu Nandi Nadi', exact: true }).count(), 0);
    assert.equal(await page.locator('#panel-bnn').count(), 0);
    await nav('Brihat Jataka');
    await page.locator('.bj-strength-graphs').waitFor();
    const bjnav = page.getByRole('navigation', { name: 'Brihat Jataka views' });
    for (const view of ['Strengths', 'Dashas', 'Yogas', 'Chart readings', 'Ashtakavarga', 'Predictions']) {
      await bjnav.getByRole('button', { name: view, exact: false }).click();
      await overflow();
    }
    await bjnav.getByRole('button', { name: 'Dashas', exact: false }).click();
    await page.getByRole('combobox', { name: 'Year method' }).selectOption('pinda');
    await page.getByRole('combobox', { name: 'Starting point' }).selectOption('Moon');
    await page.getByRole('button', { name: 'Calculate worksheet', exact: true }).click();
    await page.getByRole('heading', { name: 'Pindayurdaya · Moon first' }).waitFor();
    assert.equal(await page.getByText('Settings changed. Calculate to update the report.').count(), 0);
    const periods = page.getByRole('region', { name: 'Brihat Jataka dashas and antardashas' });
    assert.equal(await periods.locator('tbody > tr').count(), 8);
    assert.equal(await periods.locator('tbody > tr').first().locator('td').first().innerText(), 'Moon');
    await periods.locator('summary').first().click();
    assert.ok(await periods.locator('.bj-subperiods').first().isVisible());
    await shot('brihat-dashas-desktop');
    await bjnav.getByRole('button', { name: 'Predictions', exact: false }).click();
    await shot('brihat-predictions-desktop');
    for (const width of [320, 390, 768]) {
      await page.setViewportSize({ width, height: 900 });
      await overflow();
      await bjnav.getByRole('button', { name: 'Strengths', exact: false }).click();
      await overflow();
      await bjnav.getByRole('button', { name: 'Dashas', exact: false }).click();
      await overflow();
    }
    await shot('brihat-mobile');
    await page.setViewportSize({ width: 1536, height: 1100 });
    console.log('PASS: BNN removed; Brihat strengths, dasha options, antardashas, predictions and responsive views');

    await nav('Divisional charts');
    assert.equal(await page.locator('#panel-divisional .subtab-radio').count(), 24);
    for (const code of ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D16', 'D20', 'D24', 'D27', 'D30', 'D40', 'D45', 'D60', 'D81', 'D108', 'D144']) {
      await page.locator('#panel-divisional').getByRole('tab', { name: code, exact: true }).click();
      const selected = page.locator('#panel-divisional .subtab-panel:visible');
      assert.equal(await selected.count(), 1);
      assert.equal(await selected.locator('.chart-cell:not(.blank)').count(), 12);
      assert.equal(await selected.locator('.planet-degree').count(), 9);
      assert.equal(await selected.locator('.cell-asc').count(), 1);
      assert.ok((await selected.locator('.chart-center-title').innerText()).startsWith(`${code} `));
      assert.ok((await selected.locator('.chart-center-purpose').innerText()).length > 0);
      assert.equal(await selected.locator('.amsa-ruler-table tbody tr').count(), 10);
    }
    await page.locator('#panel-divisional').getByRole('tab', { name: 'D9', exact: true }).click();
    assert.ok(await page.locator('#subtab-D9').isChecked());
    assert.equal(await page.locator('#panel-divisional .subtab-panel:visible').count(), 1);
    await shot('divisional-desktop');
    await nav('Ashtakavarga');
    assert.equal(await page.locator('#panel-ashtakavarga .ashtakavarga-tile').count(), 9);
    await shot('ashtakavarga-desktop');
    await nav('Strengths');
    const balaPanel = page.locator('#panel-balas');
    assert.equal(await balaPanel.getByRole('tab').count(), 14);
    await balaPanel.getByRole('tab', { name: 'Shadbala Total', exact: true }).click();
    assert.equal(await balaPanel.locator('.strength-column').count(), 7);
    assert.equal(await balaPanel.locator('.strength-required').count(), 7);
    await shot('shadbala-desktop');
    for (const name of ['Shadvarga · 6 divisions', 'Saptavarga · 7 divisions', 'Dashavarga · 10 divisions', 'Shodashavarga · 16 divisions']) {
      await balaPanel.getByRole('tab', { name, exact: true }).click();
      assert.equal(await balaPanel.locator('.strength-graph').count(), 1);
      assert.equal(await balaPanel.locator('.strength-column').count(), 7);
    }
    await shot('vimshopaka-desktop');
    await balaPanel.getByRole('tab', { name: 'Bhava Bala · 12 houses', exact: true }).click();
    assert.equal(await balaPanel.locator('.strength-column').count(), 12);
    await shot('balas-desktop');
    assert.equal(await page.locator('.paddhati-tabs').count(), 0);
    assert.equal(await page.getByRole('navigation', { name: 'Astrology sections' }).getByRole('button', { name: /Paddhati/ }).count(), 3);
    await nav('Bhrigu Chakra Paddhati');
    await page.getByLabel('Running year', {exact: true}).selectOption('120');
    assert.ok(await page.getByRole('heading', {name: 'Activation for year 120', exact: false}).isVisible());
    await nav('Bhrigu Sarala Paddhati');
    assert.ok(await page.locator('#panel-bsp').isVisible());
    assert.equal(await page.locator('#panel-bcp:visible').count(), 0);
    await shot('bhrigu-sarala-desktop');
    await nav('Padma Chakra Paddhati');
    await page.getByLabel('Running year', {exact: true}).selectOption('120');
    assert.ok(await page.getByRole('heading', {name: 'Activation for year 120', exact: false}).isVisible());
    await shot('padma-desktop');
    await nav('Bhrigu Chakra Paddhati');
    assert.equal(await page.getByLabel('Running year', {exact: true}).inputValue(), '120');
    assert.ok(await page.getByRole('heading', {name: 'Activation for year 120', exact: false}).isVisible());
    await shot('bhrigu-chakra-desktop');
    console.log('PASS: all divisional charts, bindu tiles, Balas tabs, and year 120 selectors');

    await nav('Dasha');
    await page.locator('.vimshottari-level[data-level="4"] .vimshottari-period').first().waitFor();
    assert.equal(await page.locator('.vimshottari-period').count(), 45);
    assert.equal(await page.locator('.vimshottari-period[aria-pressed="true"]').count(), 5);
    assert.ok(await page.getByRole('heading', { name: 'Prana', exact: true }).isVisible());
    await page.locator('.vimshottari-explorer').screenshot({ path: path.join(output, 'dasha-detail-desktop.png') });
    console.log('PASS: five dasha levels together through Prana');

    await page.getByRole('button', { name: 'Edit birth details', exact: true }).click();
    assert.equal(await page.locator('#manual_latitude').inputValue(), '13.0827');
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#node_type').selectOption('true');
    await page.locator('#house_system').selectOption('placidus');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('.rasi-grid').waitFor();
    assert.ok((await page.locator('.birth-ribbon').innerText()).toLowerCase().includes('true nodes'));
    assert.ok((await page.locator('.birth-ribbon').innerText()).toLowerCase().includes('placidus'));
    console.log('PASS: editing, non-default node/house settings, and retained inputs');

    await nav('Compatibility');
    await page.getByRole('button', { name: 'Add second person', exact: true }).click();
    assert.ok(await page.locator('#include_match').isChecked());
    assert.equal(await page.locator('#birth_date').inputValue(), '15/06/1990');
    assert.equal(await page.locator('#b_birth_date').getAttribute('placeholder'), 'DD/MM/YYYY');
    await page.locator('#b_name').fill('Second chart');
    await page.locator('#b_birth_date').fill('22/11/1992');
    await page.locator('#b_birth_hour').selectOption('2');
    await page.locator('#b_birth_minute').selectOption('45');
    await page.locator('#b_birth_meridiem').selectOption('PM');
    await page.getByText('Advanced: exact coordinates for second person', { exact: true }).click();
    await page.locator('#b_manual_latitude').fill('12.9716');
    await page.locator('#b_manual_longitude').fill('77.5946');
    await page.locator('#b_manual_utc_offset_hours').fill('5.5');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('#panel-compat').waitFor();
    assert.ok((await page.locator('#panel-compat').innerText()).includes('Nadi'));
    assert.ok((await page.locator('#panel-compat').innerText()).includes('Mangal Dosha'));
    await shot('compatibility-desktop');
    console.log('PASS: complete two-person compatibility workflow');

    await nav('Birth chart');
    for (const width of [1280, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await overflow();
      const clipped = await page.locator('.rasi-cell').evaluateAll(cells => cells.filter(cell => {
        const last = cell.querySelector('.rasi-planets');
        return last.getBoundingClientRect().bottom > cell.getBoundingClientRect().bottom + 1;
      }).map(cell => cell.textContent));
      assert.deepEqual(clipped, [], `Chart labels must fit at ${width}px`);
      if (width === 390) await shot('chart-mobile');
    }
    await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await nav('Strengths');
    assert.ok(await page.locator('#panel-balas').isVisible());
    await overflow();
    await page.getByLabel('Strength view', { exact: true }).selectOption('bhava');
    await overflow();
    await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await nav('Divisional charts');
    for (const code of ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D16', 'D20', 'D24', 'D27', 'D30', 'D40', 'D45', 'D60', 'D81', 'D108', 'D144']) {
      await page.getByRole('tab', { name: code, exact: true }).click();
      const clipped = await page.locator('#panel-divisional .subtab-panel:visible .chart-cell:not(.blank), #panel-divisional .subtab-panel:visible .chart-center').evaluateAll(cells => cells.filter(cell => {
        const parent = cell.getBoundingClientRect();
        return Array.from(cell.children).some(child => {
          const bounds = child.getBoundingClientRect();
          return bounds.top < parent.top - 1 || bounds.bottom > parent.bottom + 1 || child.scrollHeight > child.clientHeight + 1;
        });
      }).map(cell => cell.textContent));
      assert.deepEqual(clipped, [], `${code} chart text must fit at 320px`);
    }
    await overflow();
    await shot('divisional-mobile');
    await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await nav('Padma Chakra Paddhati');
    await page.getByLabel('Running year', {exact: true}).selectOption('120');
    await overflow();
    await page.locator('.mobile-toolbar').getByRole('button', { name: 'Edit birth details', exact: true }).click();
    await overflow();
    await shot('birth-mobile');
    console.log('PASS: responsive layout at 1280, 1024, 768, 390 and 320px');

    await page.setViewportSize({ width: 1536, height: 1100 });
    await page.locator('#include_match').uncheck();
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#manual_latitude').fill('');
    await page.locator('#manual_longitude').fill('');
    await page.locator('#manual_utc_offset_hours').fill('');
    await page.locator('#place_name').fill('Zzzznotarealplacexyz123');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('.birth-report .error').waitFor();
    assert.ok((await page.locator('.birth-report .error').innerText()).includes('No place found'));
    assert.equal(await page.locator('#name').inputValue(), 'Design check');
    await page.locator('#place_name').fill('Haripur');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('.candidate-list').waitFor();
    assert.ok(await page.locator('.candidate-form button').count() > 1);
    assert.equal(await page.locator('#b_name').inputValue(), 'Second chart');
    await shot('place-selection-desktop');
    await page.locator('.candidate-form button').first().click();
    await page.locator('.rasi-grid').waitFor();
    assert.equal(await page.locator('.planet-table tbody tr').count(), 9);
    assert.ok((await page.locator('.birth-ribbon').innerText()).includes('Haripur'));
    console.log('PASS: friendly validation, retained form data, and first-person place selection');

    await page.getByRole('button', { name: 'Edit birth details', exact: true }).click();
    await page.locator('#include_match').check();
    await page.getByText('Advanced settings', { exact: true }).click();
    await page.locator('#manual_latitude').fill('13.0827');
    await page.locator('#manual_longitude').fill('80.2707');
    await page.locator('#manual_utc_offset_hours').fill('5.5');
    await page.getByText('Advanced: exact coordinates for second person', { exact: true }).click();
    await page.locator('#b_manual_latitude').fill('');
    await page.locator('#b_manual_longitude').fill('');
    await page.locator('#b_manual_utc_offset_hours').fill('');
    await page.locator('#b_place_name').fill('Haripur');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    await page.locator('.candidate-list').waitFor();
    assert.ok((await page.locator('.birth-report').innerText()).includes('Which place did you mean for the second person?'));
    assert.equal(await page.locator('#manual_latitude').inputValue(), '13.0827');
    await page.locator('.candidate-form button').first().click();
    await page.locator('#panel-compat').waitFor();
    assert.ok((await page.locator('#panel-compat').innerText()).includes('Nadi'));
    console.log('PASS: second-person place selection preserves the first chart and completes compatibility');

    const standalone = await page.request.post(`${origin}/dasha-detail`, { form: { lord: 'invalid' } });
    const standaloneHtml = await standalone.text();
    await page.route('**/standalone-dasha-check', route => route.fulfill({ status: 200, contentType: 'text/html', body: standaloneHtml }));
    await page.goto(`${origin}/standalone-dasha-check`);
    await page.locator('.dasha-workspace').waitFor();
    assert.ok((await page.locator('.dasha-workspace').innerText()).includes('Could not compute sub-periods'));
    await nav('Birth chart');
    await page.waitForURL(`${origin}/`);
    await page.locator('.birth-workspace').waitFor({ state: 'visible' });
    await page.locator('.birth-workspace #birth_date').waitFor();
    assert.ok(await page.locator('.birth-workspace').isVisible());
    console.log('PASS: standalone dasha validation and navigation back to the birth form');

    assert.deepEqual(errors, [], 'No browser runtime errors');
    assert.deepEqual(external, [], 'App must work with all external requests blocked');
    console.log(`PASS: offline runtime and no browser errors. Screenshots: ${output}`);
  } catch (error) {
    await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
    console.error(error);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
