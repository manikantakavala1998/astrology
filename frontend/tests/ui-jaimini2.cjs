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
  const errors = [], external = [], inheritedCalls = [], bookCalls = [];
  page.on('pageerror', e => errors.push(e.message));
  page.setDefaultTimeout(60000);
  await page.route('**/*', route => {
    const url = route.request().url();
    if (new URL(url).origin !== origin) { external.push(url); return route.abort(); }
    if (url.includes('/api/jaimini/subperiods')) inheritedCalls.push(url);
    if (url.includes('/api/jaimini2/subperiods')) bookCalls.push(url);
    return route.continue();
  });
  const panel = page.locator('#panel-jaimini2');
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
    const chartResponse = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname === '/');
    await page.getByRole('button', { name: 'Generate chart', exact: true }).click();
    const chartHtml = await (await chartResponse).text();
    const report = JSON.parse(chartHtml.match(/<script id="astro-state" type="application\/json">(.*?)<\/script>/s)[1]).jaimini2;
    await page.locator('.rasi-grid').waitFor();
    const nav = page.getByRole('navigation', { name: 'Astrology sections' });
    const labels = await nav.getByRole('button').allTextContents();
    assert.equal(labels.findIndex(s => s.trim().endsWith('Jaimini South')), labels.findIndex(s => s.trim().endsWith('Jaimini North')) + 1);
    await nav.getByRole('button', { name: 'Jaimini South', exact: true }).click();
    await panel.getByRole('table', { name: 'Jaimini South calculation workspace' }).waitFor();
    await panel.locator('.jaimini-dasha-columns[aria-busy="false"]').waitFor();
    await page.screenshot({ path: path.join(output, 'jaimini2-dashboard-desktop.png'), fullPage: true });
    await panel.getByRole('button', { name: 'Open Chara karakas', exact: true }).click();
    const karakas = panel.getByRole('table', { name: 'Chara Karakas', exact: true });
    await karakas.waitFor();
    assert.equal(await karakas.locator('tbody tr').count(), 7);
    assert.ok((await karakas.locator('tbody tr').first().innerText()).includes('Mercury'));
    assert.equal(await panel.getByRole('tab').count(), 11);
    assert.equal(await panel.getByRole('button', { name: '8 karakas', exact: true }).count(), 0);
    await panel.locator('.jaimini-dasha-columns[aria-busy="false"]').waitFor();
    await tab('Rashi Aspects').click();
    assert.equal(await panel.getByRole('table').locator('tbody tr').count(), 9);
    await tab('Arudha Padas').click();
    assert.equal(await panel.getByRole('table').locator('tbody tr').count(), 12);
    await tab('Upapada').click();
    assert.equal(await panel.getByRole('table', { name: 'Book Upapada research variants' }).locator('tbody tr').count(), 2);
    await tab('Argala').click();
    await panel.getByLabel('Jaimini South Argala target').selectOption('Aquarius');
    assert.equal(await panel.getByRole('table').locator('tbody tr').count(), 7);
    await tab('Yogada & Kevala').click();
    for (const kind of ['yogada', 'kevala']) {
      const name = kind === 'yogada' ? 'Yogada' : 'Kevala';
      const expected = [...new Set(report.schemes['7'].yogas.filter(y => y.kind === kind && y.present).flatMap(y => y.planets))];
      const shown = panel.getByRole('table', { name: `${name} qualifying planets` });
      assert.deepEqual(await shown.locator('tbody th').evaluateAll(rows => rows.map(row => row.querySelector('[class^="planet-color-"]').textContent)), expected);
      if (kind === 'yogada') {
        for (let index = 0; index < expected.length; index++) {
          const condition = report.schemes['7'].yogas.find(row => row.variant === 'multi_chart' && row.planets.includes(expected[index]));
          assert.deepEqual(await shown.locator('tbody tr').nth(index).locator('td').allTextContents(), ['D1', 'D3', 'D9'].map(chart => condition.matched_charts.includes(chart) ? '✓' : '—'));
        }
      } else {
        assert.ok((await shown.innerText()).includes('H9'));
        assert.ok((await shown.innerText()).includes('Taurus · Scorpio'));
      }
    }
    assert.equal(await panel.getByRole('table').count(), 2);
    assert.ok(!(await panel.innerText()).includes('Amatyakaraka support'));
    await page.screenshot({ path: path.join(output, 'jaimini2-yogada-kevala-desktop.png'), fullPage: true });
    await tab('Sign Strength').click();
    const graph = panel.getByRole('figure', { name: 'Jaimini South relative sign strength graph' });
    assert.equal(await graph.getByRole('button').count(), 12);
    for (const row of report.strengths) {
      const bar = graph.locator(`[data-sign="${row.sign}"]`);
      assert.equal(await bar.getAttribute('data-rank'), String(row.rank));
      assert.ok(Math.abs(await bar.locator('.jaimini2-strength-bar').evaluate(node => parseFloat(node.style.height)) - (13 - row.rank) / 12 * 100) < .0001);
    }
    await graph.locator('[data-sign="Aries"]').click();
    assert.ok((await panel.getByRole('region', { name: 'Selected sign calculation' }).innerText()).includes('Aries'));
    await page.screenshot({ path: path.join(output, 'jaimini2-sign-strength-desktop.png'), fullPage: true });
    await panel.getByText('Rules & calculations', { exact: true }).click();
    assert.equal(await panel.getByRole('table', { name: 'Book sign strength hierarchy' }).locator('tbody tr').count(), 12);
    await tab('Ayurdaya').click();
    assert.ok((await panel.innerText()).includes('Lagna / Dwaya Hora Lagna'));
    await tab('Dashas').click();
    const select = panel.getByLabel('Jaimini South dasha method');
    assert.equal(await select.locator('option').count(), 38);
    const methods = await select.locator('option').evaluateAll(options => options.map(o => o.value));
    for (const method of methods) {
      await select.selectOption(method);
      await page.waitForFunction(() => !document.querySelector('#panel-jaimini2 .jaimini-dasha-controls [role="status"]')?.textContent.includes('Calculating'));
      await overflow();
      assert.ok(await panel.locator('.jaimini-dasha-column tbody tr').count() || await panel.locator('.hint').count(), method + ' has dates or an explanation');
      if (await panel.locator('.jaimini-dasha-column tbody tr').count()) {
        assert.equal(await panel.locator('.jaimini-dasha-column').count(), 3, method + ' has all three levels');
        assert.equal(await panel.locator('.jaimini-dasha-column:last-child tbody tr').count(), 12);
      }
    }
    await select.selectOption('chara');
    await panel.getByLabel('Jaimini dasha date and time').fill('1998-09-04T00:03');
    await panel.locator('.jaimini-dasha-columns[aria-busy="false"]').waitFor();
    assert.ok((await panel.locator('.jaimini-dasha-column:first-child .is-selected').innerText()).includes('Leo'));
    assert.ok((await panel.locator('.jaimini-dasha-column:first-child .is-selected').innerText()).includes('04/09/98'));
    await page.screenshot({ path: path.join(output, 'jaimini2-dashas-desktop.png'), fullPage: true });
    await tab('Predictions').click();
    assert.equal(await panel.locator('.jaimini2-reading-grid article').count(), 6);
    const predictionTopic = name => panel.getByRole('navigation', { name: 'Jaimini South prediction topics' }).getByRole('button', { name, exact: true });
    for (const module of report.predictions.modules) {
      await predictionTopic(module.title).click();
      assert.ok((await panel.innerText()).includes(module.anchor));
      await overflow();
    }
    await predictionTopic('Arudha Lagna & all padas').click();
    await panel.getByText('Rules & calculations', { exact: true }).click();
    assert.equal(await panel.getByRole('table', { name: 'All arudha reading connections' }).locator('tbody tr').count(), 12);
    await predictionTopic('Standard Upapada').click();
    const ul = panel.getByLabel('Prediction Upapada convention');
    assert.equal(await ul.locator('option').count(), 3);
    for (let index = 0; index < 3; index++) { await ul.selectOption(String(index)); assert.ok((await panel.innerText()).includes(report.predictions.upapada_readings[index].anchor)); }
    await predictionTopic('Swamsha').click();
    await panel.getByText('Rules & calculations', { exact: true }).click();
    assert.ok((await panel.getByRole('table', { name: 'Swamsha house positions' }).locator('tbody tr').first().innerText()).includes('Mercury'));
    await predictionTopic('Kevala planet predictions').click();
    await panel.getByLabel('Prediction planet').selectOption('Saturn');
    assert.equal(await panel.locator('.jaimini2-planet-readings > section').count(), 1);
    assert.ok((await panel.locator('.jaimini2-planet-readings').innerText()).includes('Supportive'));
    await predictionTopic('Dasha periods').click();
    await panel.getByLabel('Jaimini South prediction date').fill('1998-09-04T00:03');
    await panel.getByLabel('Jaimini South prediction method').selectOption('navamsa');
    assert.ok((await panel.innerText()).includes('D9 reading'));
    await panel.getByText('Prediction conditions checked', { exact: true }).click();
    assert.equal(await panel.getByRole('table', { name: 'Book dasha prediction conditions' }).locator('tbody tr').count(), 3);
    await panel.getByLabel('Jaimini South prediction method').selectOption('nisarga');
    assert.ok((await panel.locator('.hint').innerText()).includes('Not applicable'));
    await panel.getByLabel('Jaimini South prediction method').selectOption('chara');
    assert.ok((await panel.getByRole('table', { name: 'Jaimini South dasha prediction comparison' }).innerText()).includes('Mixed'));
    await panel.getByRole('group', { name: 'Filter dasha indications' }).getByRole('button', { name: 'Supportive · good indications', exact: true }).click();
    assert.ok(await panel.getByRole('table', { name: 'Jaimini South dasha prediction comparison' }).locator('tbody tr').count());
    await panel.getByRole('group', { name: 'Filter dasha indications' }).getByRole('button', { name: 'All periods', exact: true }).click();
    await panel.getByRole('button', { name: 'Read Pisces period', exact: true }).click();
    assert.ok((await panel.innerText()).includes('Pisces period · D1 reading'));
    await page.screenshot({ path: path.join(output, 'jaimini2-predictions-desktop.png'), fullPage: true });
    for (const width of [1366, 390, 320]) {
      await page.setViewportSize({ width, height: 768 });
      for (const name of ['Charts & Karakas', 'Predictions', 'Dashas', 'Argala', 'Sign Strength', 'Yogada & Kevala', 'Ayurdaya', 'Advanced', 'Upapada']) {
        await tab(name).click(); await overflow();
      }
      await tab('Yogada & Kevala').click();
      const clippedTables = await panel.locator('.jaimini2-yoga-panel .table-scroll').evaluateAll(nodes => nodes.filter(node => node.scrollWidth > node.clientWidth + 1).length);
      assert.equal(clippedTables, 0, `Yogada/Kevala tables fit without sideways scrolling at ${width}px`);
      await tab('Predictions').click();
      for (const module of report.predictions.modules) { await predictionTopic(module.title).click(); await overflow(); }
      await predictionTopic('Dasha periods').click(); await overflow();
      await tab('Charts & Karakas').click();
      for (const chart of ['D1', 'D3', 'D9', 'Karakamsha', 'Swamsha']) {
        await panel.getByRole('button', { name: chart, exact: true }).click();
        const clipped = await panel.locator('.rasi-cell, .rasi-center').evaluateAll(cells => cells.filter(cell => [...cell.children].some(child => {
          const c = child.getBoundingClientRect(), b = cell.getBoundingClientRect();
          return c.bottom > b.bottom + 1 || c.right > b.right + 1 || child.scrollWidth > child.clientWidth + 1 || child.scrollHeight > child.clientHeight + 1;
        })).map(cell => cell.textContent));
        assert.deepEqual(clipped, [], `Chart fits at ${width}px (${chart})`);
      }
      if (width === 1366) {
        await page.evaluate(() => scrollTo(0, 0));
        const box = await panel.locator('.rasi-grid').boundingBox();
        if (box.y + box.height >= 768) { await page.screenshot({ path: path.join(output, 'jaimini2-laptop-fit.png'), fullPage: true }); console.log('Laptop chart bounds:', box); }
        assert.ok(box.y + box.height < 768, 'Complete chart visible on laptop');
      }
      if (width === 390) {
        await tab('Sign Strength').click();
        await page.screenshot({ path: path.join(output, 'jaimini2-sign-strength-mobile.png'), fullPage: true });
        await tab('Yogada & Kevala').click();
        await page.screenshot({ path: path.join(output, 'jaimini2-yogada-kevala-mobile.png'), fullPage: true });
        await tab('Predictions').click();
        await page.screenshot({ path: path.join(output, 'jaimini2-predictions-mobile.png'), fullPage: true });
      }
    }
    assert.deepEqual(errors, []); assert.deepEqual(external, []); assert.deepEqual(inheritedCalls, []);
    assert.ok(bookCalls.length > 0);
    console.log('PASS: Jaimini South qualifying Yogada/Kevala planets, tied strength ranks and interactive graph, 38 dasha entries, three independent levels and laptop/mobile fit');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
