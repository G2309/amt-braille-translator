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
      const rellenos = b.querySelectorAll('.relleno');
      // Con data-antes la primera barra es la referencia y la segunda el valor nuevo
      if (b.dataset.antes) rellenos[0].style.width = `${(Number(b.dataset.antes) / max) * 100}%`;
      rellenos[rellenos.length - 1].style.width = `${(v / max) * 100}%`;
      const meta = grupo.dataset.meta;
      if (meta) b.querySelector('.pista').insertAdjacentHTML('beforeend', `<span class="meta" style="left:${(Number(meta) / max) * 100}%"></span>`);
    });
  });

  // Carrusel de resultados: cada paso muestra el objetivo y luego su resultado
  const carruseles = [...document.querySelectorAll('.carrusel')].map((raiz) => {
    const pasos = [...raiz.querySelectorAll('.paso-oe')];
    const alternar = raiz.querySelector('[data-carrusel="alternar"]');
    const anterior = raiz.querySelector('[data-carrusel="anterior"]');
    const siguiente = raiz.querySelector('[data-carrusel="siguiente"]');
    const estado = raiz.querySelector('[aria-live]');
    const puntos = raiz.querySelector('.puntos');
    let i = 0, resultado = false;
    pasos.forEach((paso, k) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = k < pasos.length - 1 ? k + 1 : 'G';
      b.setAttribute('aria-label', paso.getAttribute('aria-label'));
      b.addEventListener('click', () => mostrar(k, false));
      puntos.append(b);
    });
    function mostrar(k, verResultado, anunciar = true) {
      i = Math.max(0, Math.min(k, pasos.length - 1));
      resultado = verResultado;
      pasos.forEach((paso, n) => {
        paso.hidden = n !== i;
        paso.classList.toggle('ver-resultado', n === i && resultado);
      });
      [...puntos.children].forEach((b, n) => (n === i ? b.setAttribute('aria-current', 'step') : b.removeAttribute('aria-current')));
      alternar.textContent = resultado ? 'Ver objetivo' : 'Ver resultado';
      anterior.disabled = i === 0 && !resultado;
      siguiente.disabled = i === pasos.length - 1 && resultado;
      const cara = pasos[i].querySelector(resultado ? '.cara.resultado' : '.cara.objetivo');
      if (anunciar) estado.textContent = `${cara.querySelector('.etiqueta').textContent}. ${cara.querySelector('h3').textContent}`;
    }
    // Avanza de objetivo a resultado y de resultado al siguiente objetivo; devuelve false en los extremos
    function paso(dir) {
      if (dir > 0) {
        if (!resultado) mostrar(i, true);
        else if (i < pasos.length - 1) mostrar(i + 1, false);
        else return false;
      } else {
        if (resultado) mostrar(i, false);
        else if (i > 0) mostrar(i - 1, true);
        else return false;
      }
      return true;
    }
    alternar.addEventListener('click', () => mostrar(i, !resultado));
    anterior.addEventListener('click', () => paso(-1));
    siguiente.addEventListener('click', () => paso(1));
    mostrar(0, false, false);
    return { raiz, paso };
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
      if (!caja || s.classList.contains('hero')) return;
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

  // En modo presentación las flechas recorren primero el carrusel de la sección actual
  function pasoCarrusel(dir) {
    const actual = principales()[indice];
    const c = carruseles.find((x) => actual && actual.contains(x.raiz));
    return c ? c.paso(dir) : false;
  }

  document.addEventListener('keydown', (e) => {
    if (e.target.closest('input, textarea') || (e.key === ' ' && e.target.closest('button, a'))) return;
    const k = e.key;
    if (k === 'p' || k === 'P') alternarPresentacion();
    else if (k === 'n' || k === 'N') cuerpo.classList.toggle('con-notas');
    else if (k === 'r' || k === 'R') { cuerpo.classList.toggle('ver-respaldo'); marcar(indice); }
    else if (!cuerpo.classList.contains('presentando')) return;
    else if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(k)) { e.preventDefault(); if (!pasoCarrusel(1)) ir(indice + 1); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(k)) { e.preventDefault(); if (!pasoCarrusel(-1)) ir(indice - 1); }
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
