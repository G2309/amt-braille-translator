// Audita la PWA servida en local con axe-core por modo y ancho, Lighthouse e instalabilidad
import fs from 'node:fs';
import puppeteer from 'puppeteer-core';
import { AxePuppeteer } from '@axe-core/puppeteer';
import lighthouse from 'lighthouse';

// Por omisión la compilación local servida en 8765; AUDITAR_URL apunta a la PWA desplegada
const URL = process.env.AUDITAR_URL ?? 'http://localhost:8765/amt-braille-translator/';
const exe = process.env.CHROME;
const modos = [null, 'tutor', 'bajaVision', 'nulaVision'];
const anchos = [[320, 640], [768, 1024], [1280, 800]];
const salida = { axe: [], lighthouse: [], instalable: null };
fs.mkdirSync('capturas', { recursive: true });

const navegador = await puppeteer.launch({ executablePath: exe, args: ['--no-sandbox', '--remote-debugging-port=9333'] });

async function abrir(modo, [w, h]) {
  const p = await navegador.newPage();
  await p.setViewport({ width: w, height: h });
  await p.goto(URL);
  await p.evaluate((m) => { localStorage.clear(); if (m) localStorage.setItem('flutter.modo', JSON.stringify(m)); }, modo);
  await p.goto(URL, { waitUntil: 'networkidle0' });
  await p.waitForSelector('flt-semantics', { timeout: 30000 });
  await new Promise((r) => setTimeout(r, 1500));
  return p;
}

for (const modo of modos) {
  for (const tam of anchos) {
    const p = await abrir(modo, tam);
    const r = await new AxePuppeteer(p).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze();
    const nombres = await p.$$eval('flt-semantics[role], flt-semantics button, input, [role=button]', (ns) => ns.map((n) => n.getAttribute('aria-label') || n.textContent.trim()).filter(Boolean));
    salida.axe.push({
      modo: modo ?? 'sin_elegir', ancho: tam[0],
      reglas_aprobadas: r.passes.length, violaciones: r.violations.length,
      nodos_con_violacion: r.violations.reduce((a, v) => a + v.nodes.length, 0),
      revisar_a_mano: r.incomplete.length,
      detalle: r.violations.map((v) => ({ regla: v.id, impacto: v.impact, nodos: v.nodes.length, ejemplo: v.nodes[0]?.html.slice(0, 160) })),
      elementos_con_nombre: nombres.length,
    });
    await p.screenshot({ path: 'capturas/captura_' + (modo ?? 'sin_elegir') + '_' + tam[0] + '.png' });
    await p.close();
  }
}

// Errores de instalabilidad que Chrome reporta para la PWA
const p = await abrir(null, [1280, 800]);
const cdp = await p.createCDPSession();
salida.instalable = (await cdp.send('Page.getInstallabilityErrors')).installabilityErrors;
await p.close();

for (const modo of modos) {
  for (const formFactor of ['mobile', 'desktop']) {
    const p = await abrir(modo, formFactor === 'mobile' ? [412, 823] : [1350, 940]);
    await p.close();
    const r = await lighthouse(URL, { port: 9333, output: 'json', onlyCategories: ['accessibility', 'best-practices', 'seo'], formFactor, screenEmulation: formFactor === 'desktop' ? { mobile: false, width: 1350, height: 940, deviceScaleFactor: 1 } : undefined, disableStorageReset: true });
    const c = r.lhr.categories;
    const fallos = Object.values(r.lhr.audits).filter((a) => a.score === 0 && a.scoreDisplayMode === 'binary').map((a) => a.id);
    salida.lighthouse.push({ modo: modo ?? 'sin_elegir', formato: formFactor, accesibilidad: Math.round(c.accessibility.score * 100), buenas_practicas: Math.round(c['best-practices'].score * 100), seo: Math.round(c.seo.score * 100), auditorias_fallidas: fallos });
  }
}

await navegador.close();
fs.writeFileSync(process.argv[2], JSON.stringify(salida, null, 2));
console.log(JSON.stringify({ axe: salida.axe.map((a) => [a.modo, a.ancho, a.violaciones, a.reglas_aprobadas]), lh: salida.lighthouse.map((l) => [l.modo, l.formato, l.accesibilidad, l.buenas_practicas, l.seo, l.auditorias_fallidas.join(',')]), instalable: salida.instalable }));
