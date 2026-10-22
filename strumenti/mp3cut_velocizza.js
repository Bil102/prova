// Accelera un audio con mp3cut.net (Cambia velocità), come si fa a mano dal sito.
// uso: node strumenti/mp3cut_velocizza.js input.mp3 1.19 output.mp3
// Richiede Playwright + Chromium e i domini mp3cut.net, *.mp3cut.net, *.123apps.com, *.123apps.io.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/opt/node-tools/node_modules/playwright');
const [inp, target, out] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const p = await ctx.newPage();
  await p.goto('https://mp3cut.net/it/change-speed', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.setInputFiles('input.md-file-picker__input', inp);
  await p.waitForSelector('.el-slider', { state: 'visible', timeout: 120000 });
  await p.waitForTimeout(2000);
  // il valore aggiornato si legge solo nel testo "1.19x" accanto al cursore
  const val = async () => parseFloat((await p.locator('.slider-wrap').first().locator('xpath=..').innerText()).match(/([\d.]+)x/)[1]);
  const t = parseFloat(target);
  const run = await p.locator('.el-slider__runway').first().boundingBox();
  const y = run.y + run.height / 2;
  let x = run.x + run.width * (t - 0.5) / 2.5;
  // un clic che cade sopra il cursore viene ignorato: prima lo si sposta lontano, poi si clicca
  const lontano = run.x + run.width * (t < 1.75 ? 0.95 : 0.05);
  for (let i = 0; i < 30; i++) {  // clic sulla barra, poi ritocco di mezzo pixel
    await p.mouse.click(lontano, y); await p.waitForTimeout(200);
    await p.mouse.click(x, y); await p.waitForTimeout(300);
    const v = await val();
    if (Math.abs(v - t) < 0.005) break;
    x += v < t ? 0.5 : -0.5;
  }
  console.log('velocità impostata:', await val());
  await p.click('button.btn-cut');
  // dopo l'elaborazione compare la schermata con "Salva" / "Indietro": il secondo "Salva" scarica
  await p.getByText('Indietro', { exact: true }).filter({ visible: true }).first().waitFor({ timeout: 180000 });
  const salva = p.getByText('Salva', { exact: true }).filter({ visible: true }).first();
  const [d] = await Promise.all([p.waitForEvent('download', { timeout: 180000 }), salva.click()]);
  await d.saveAs(out);
  console.log('scaricato:', out);
  await b.close();
})().catch(e => { console.error('ERRORE', e.message); process.exit(1); });
