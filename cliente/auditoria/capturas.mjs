// Capturas de la PWA en pantalla de teléfono para la tesis; el modo tutor completa una conversión real contra la API
import fs from 'node:fs';
import puppeteer from 'puppeteer-core';

const URL = process.env.AUDITAR_URL ?? 'http://localhost:8765/amt-braille-translator/';
const AUDIO = process.argv[2];
const TAM = { width: 390, height: 844 };
fs.mkdirSync('capturas', { recursive: true });
const navegador = await puppeteer.launch({ executablePath: process.env.CHROME, args: ['--no-sandbox'] });

async function abrir(modo, alto = TAM.height) {
  const p = await navegador.newPage();
  await p.setViewport({ width: TAM.width, height: alto, deviceScaleFactor: 2 });
  await p.goto(URL);
  await p.evaluate((m) => { localStorage.clear(); if (m) localStorage.setItem('flutter.modo', JSON.stringify(m)); }, modo);
  await p.goto(URL, { waitUntil: 'networkidle0' });
  await p.waitForSelector('flt-semantics', { timeout: 30000 });
  await new Promise((r) => setTimeout(r, 1500));
  return p;
}

// Pulsa el nodo de semántica cuyo texto o etiqueta contiene el texto dado
async function pulsar(p, texto) {
  let mejor = null;
  for (const n of await p.$$('flt-semantics')) {
    const t = await n.evaluate((e) => (e.getAttribute('aria-label') || '') + ' ' + e.textContent);
    const caja = await n.boundingBox();
    if (t.includes(texto) && caja && (!mejor || caja.width * caja.height < mejor.area)) mejor = { n, area: caja.width * caja.height, caja };
  }
  if (!mejor) throw new Error('no se encontró ' + texto);
  await p.mouse.click(mejor.caja.x + mejor.caja.width / 2, mejor.caja.y + mejor.caja.height / 2);
}

for (const modo of [null, 'bajaVision', 'nulaVision']) {
  const p = await abrir(modo);
  await p.screenshot({ path: `capturas/telefono_${modo ?? 'seleccion'}.png` });
  await p.close();
}

// Conversión completa en modo tutor, con una ventana alta para que entre la vista previa
const p = await abrir('tutor', 1500);
// El selector de archivos crea un input que se intercepta para cargarle el audio sin abrir el diálogo
await p.evaluate(() => {
  const original = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function () {
    if (this.type === 'file') { this.id = 'entrada-audio'; document.body.appendChild(this); } else original.call(this);
  };
});
await pulsar(p, 'Elegir grabación');
const entrada = await p.waitForSelector('#entrada-audio', { timeout: 15000 });
await entrada.uploadFile(AUDIO);
await new Promise((r) => setTimeout(r, 1500));
await pulsar(p, 'Convertir a Braille');
await p.waitForFunction(() => document.body.innerText.includes('Descargar') || [...document.querySelectorAll('flt-semantics')].some((e) => (e.getAttribute('aria-label') || e.textContent).includes('Descargar')), { timeout: 600000 });
await new Promise((r) => setTimeout(r, 2000));
await p.screenshot({ path: 'capturas/telefono_tutor_resultado.png' });
await navegador.close();
console.log('capturas listas');
