// Modo presentación: navegación por teclado, notas del orador, reloj por sección y anillos de métrica
(() => {
  const params = new URLSearchParams(location.search);
  const minutosTotales = Number(params.get('min')) || 20;
  const cuerpo = document.body;
  const progreso = document.querySelector('.progreso');
  const reloj = document.querySelector('.orador .reloj');
  const nombreSeccion = document.querySelector('.orador .seccion');

  // Anillos dibujados a partir de data-valor y data-color
  document.querySelectorAll('.anillo[data-valor]').forEach((el) => {
    const valor = Number(el.dataset.valor);
    const max = Number(el.dataset.max || 100);
    const color = el.dataset.color || '#415eee';
    const r = 64, c = 2 * Math.PI * r, parte = Math.min(valor / max, 1) * c;
    const texto = el.dataset.texto || `${valor}`;
    el.insertAdjacentHTML('afterbegin', `<svg viewBox="0 0 160 160" aria-hidden="true">
      <circle cx="80" cy="80" r="${r}" fill="none" stroke="#ebf0f8" stroke-width="14"/>
      <circle cx="80" cy="80" r="${r}" fill="none" stroke="${color}" stroke-width="14" stroke-linecap="round"
        stroke-dasharray="${parte} ${c}" transform="rotate(-90 80 80)"/>
      <text x="80" y="88" text-anchor="middle" font-size="30" font-weight="600" fill="#222326" font-family="Inter, system-ui, sans-serif">${texto}</text>
    </svg>`);
  });

  // Barras con su valor y su meta en porcentaje del máximo
  document.querySelectorAll('.barras[data-max]').forEach((grupo) => {
    const max = Number(grupo.dataset.max);
    grupo.querySelectorAll('.barra').forEach((b) => {
      const v = Number(b.dataset.valor);
      b.querySelector('.relleno').style.width = `${(v / max) * 100}%`;
      const meta = grupo.dataset.meta;
      if (meta) b.querySelector('.pista').insertAdjacentHTML('beforeend', `<span class="meta" style="left:${(Number(meta) / max) * 100}%"></span>`);
    });
  });

  const principales = () => [...document.querySelectorAll('.slide')].filter((s) => cuerpo.classList.contains('ver-respaldo') || !s.classList.contains('respaldo'));
  const pesoTotal = [...document.querySelectorAll('.slide[data-peso]')].reduce((a, s) => a + Number(s.dataset.peso), 0);
  let indice = 0;
  let inicioSeccion = Date.now();

  function marcar(i) {
    const lista = principales();
    indice = Math.max(0, Math.min(i, lista.length - 1));
    lista.forEach((s, k) => s.classList.toggle('actual', k === indice));
    const actual = lista[indice];
    progreso.style.width = `${((indice + 1) / lista.length) * 100}%`;
    nombreSeccion.textContent = actual.dataset.titulo || '';
    inicioSeccion = Date.now();
    tic();
    return actual;
  }

  function ir(i) {
    const actual = marcar(i);
    // En modo presentación el salto es instantáneo, como al cambiar de diapositiva
    actual.scrollIntoView({ behavior: cuerpo.classList.contains('presentando') ? 'instant' : 'smooth', block: 'start' });
  }

  function tic() {
    const actual = principales()[indice];
    const objetivo = actual && actual.dataset.peso ? (Number(actual.dataset.peso) / pesoTotal) * minutosTotales * 60 : 0;
    const t = Math.floor((Date.now() - inicioSeccion) / 1000);
    const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;
    reloj.textContent = objetivo ? `${fmt(t)} de ${fmt(objetivo)}` : fmt(t);
    reloj.classList.toggle('tarde', objetivo && t > objetivo);
  }
  setInterval(tic, 1000);

  // En modo presentación cada sección se escala para caber en la ventana sin scroll
  function ajustar() {
    document.querySelectorAll('.slide').forEach((s) => {
      const caja = s.querySelector(':scope > .contenido, :scope > .campo');
      if (!caja) return;
      caja.style.setProperty('--escala', 1);
      if (!cuerpo.classList.contains('presentando')) return;
      const disponible = window.innerHeight - 128;
      caja.style.setProperty('--escala', Math.min(1, disponible / caja.scrollHeight).toFixed(3));
    });
  }
  window.addEventListener('resize', ajustar);

  function alternarPresentacion() {
    cuerpo.classList.toggle('presentando');
    ajustar();
    ir(indice);
  }

  document.querySelectorAll('[data-accion="presentar"]').forEach((b) => b.addEventListener('click', alternarPresentacion));

  document.addEventListener('keydown', (e) => {
    if (e.target.closest('input, textarea')) return;
    const k = e.key;
    if (k === 'p' || k === 'P') alternarPresentacion();
    else if (k === 'n' || k === 'N') cuerpo.classList.toggle('con-notas');
    else if (k === 'r' || k === 'R') { cuerpo.classList.toggle('ver-respaldo'); marcar(indice); }
    else if (!cuerpo.classList.contains('presentando')) return;
    else if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(k)) { e.preventDefault(); ir(indice + 1); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(k)) { e.preventDefault(); ir(indice - 1); }
    else if (k === 'Home') ir(0);
    else if (k === 'End') ir(principales().length - 1);
  });

  // Al hacer scroll sin teclado, la sección visible pasa a ser la actual
  const observador = new IntersectionObserver((entradas) => {
    entradas.forEach((en) => {
      if (en.isIntersecting) {
        const i = principales().indexOf(en.target);
        if (i >= 0 && i !== indice) marcar(i);
      }
    });
  }, { rootMargin: '-50% 0px -50% 0px', threshold: 0 });
  document.querySelectorAll('.slide').forEach((s) => observador.observe(s));
  marcar(0);
  if (params.has('presentar')) alternarPresentacion();
})();
