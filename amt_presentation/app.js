// Modo presentación: navegación por teclado, notas del orador, tarjetas que giran y anillos de métrica
(() => {
  const params = new URLSearchParams(location.search);
  const cuerpo = document.body;
  const progreso = document.querySelector('.progreso');

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

  const sinMovimiento = matchMedia('(prefers-reduced-motion: reduce)');
  // Gira solo la tarjeta: media vuelta hasta quedar de canto, cambia el contenido y termina el giro
  function girar(el, cambiar, dir = 1) {
    if (sinMovimiento.matches || !el.animate) { cambiar(); return; }
    const ida = el.animate([{ transform: 'perspective(1400px) rotateY(0deg)' }, { transform: `perspective(1400px) rotateY(${90 * dir}deg)` }], { duration: 200, easing: 'ease-in' });
    ida.onfinish = () => {
      cambiar();
      el.animate([{ transform: `perspective(1400px) rotateY(${-90 * dir}deg)` }, { transform: 'perspective(1400px) rotateY(0deg)' }], { duration: 260, easing: 'ease-out' });
    };
  }

  // Tarjeta de cada objetivo: el botón la gira para mostrar el resultado y volver al objetivo
  const volteos = [...document.querySelectorAll('.volteo')].map((raiz) => {
    const paso = raiz.querySelector('.paso-oe');
    const pista = raiz.querySelector('.pista-carrusel');
    const boton = raiz.querySelector('[data-volteo]');
    const estado = raiz.querySelector('[aria-live]');
    let resultado = false;
    function aplicar(v) {
      resultado = v;
      paso.classList.toggle('ver-resultado', v);
      boton.textContent = v ? 'Ver objetivo' : 'Ver resultado';
      const cara = paso.querySelector(v ? '.cara.resultado' : '.cara.objetivo');
      estado.textContent = `${cara.querySelector('.etiqueta').textContent}. ${cara.querySelector('h3').textContent}`;
    }
    function voltear(v) {
      if (v === resultado) return false;
      girar(pista, () => aplicar(v), v ? 1 : -1);
      return true;
    }
    boton.addEventListener('click', () => voltear(!resultado));
    return { raiz, paso: (dir) => voltear(dir > 0) };
  });

  // Mazos de láminas con pestañas, anterior y siguiente
  const mazos = [...document.querySelectorAll('.mazo')].map((raiz) => {
    const laminas = [...raiz.querySelectorAll('.lamina')];
    const pila = raiz.querySelector('.pila');
    const pestanas = raiz.querySelector('.pestanas');
    const anterior = raiz.querySelector('[data-mazo="anterior"]');
    const siguiente = raiz.querySelector('[data-mazo="siguiente"]');
    const estado = raiz.querySelector('[aria-live]');
    let i = 0;
    laminas.forEach((l, k) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = l.dataset.pestana;
      b.addEventListener('click', () => ir(k));
      pestanas.append(b);
    });
    function aplicar(k, anunciar) {
      i = k;
      laminas.forEach((l, n) => { l.hidden = n !== i; });
      [...pestanas.children].forEach((b, n) => (n === i ? b.setAttribute('aria-current', 'step') : b.removeAttribute('aria-current')));
      anterior.disabled = i === 0;
      siguiente.disabled = i === laminas.length - 1;
      if (anunciar) estado.textContent = laminas[i].querySelector('h3').textContent;
    }
    function ir(k) {
      if (k === i || k < 0 || k >= laminas.length) return false;
      girar(pila, () => aplicar(k, true), k > i ? 1 : -1);
      return true;
    }
    anterior.addEventListener('click', () => ir(i - 1));
    siguiente.addEventListener('click', () => ir(i + 1));
    aplicar(0, false);
    return { raiz, paso: (dir) => ir(i + dir) };
  });
  const pasables = [...volteos, ...mazos];

  const principales = () => [...document.querySelectorAll('.slide')].filter((s) => cuerpo.classList.contains('ver-respaldo') || !s.classList.contains('respaldo'));
  let indice = 0;

  function marcar(i) {
    const lista = principales();
    indice = Math.max(0, Math.min(i, lista.length - 1));
    lista.forEach((s, k) => s.classList.toggle('actual', k === indice));
    const actual = lista[indice];
    progreso.style.width = `${((indice + 1) / lista.length) * 100}%`;
    return actual;
  }

  function ir(i) {
    const actual = marcar(i);
    // En modo presentación el salto es instantáneo, como al cambiar de diapositiva
    actual.scrollIntoView({ behavior: cuerpo.classList.contains('presentando') ? 'instant' : 'smooth', block: 'start' });
  }


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

  // En modo presentación las flechas giran primero la tarjeta o el mazo de la sección actual
  function pasoCarrusel(dir) {
    const actual = principales()[indice];
    const c = pasables.find((x) => actual && actual.contains(x.raiz));
    return c ? c.paso(dir) : false;
  }

  // Glosario: la tecla G lo abre y lo cierra, Esc también lo cierra
  const glosario = document.getElementById('glosario');
  let focoPrevio = null;
  function alternarGlosario(abrir = glosario.hidden) {
    if (abrir) {
      focoPrevio = document.activeElement;
      glosario.hidden = false;
      glosario.querySelector('.glosario-caja').focus();
    } else {
      glosario.hidden = true;
      if (focoPrevio) focoPrevio.focus();
    }
  }
  glosario.querySelector('[data-accion="cerrar-glosario"]').addEventListener('click', () => alternarGlosario(false));
  glosario.addEventListener('click', (e) => { if (e.target === glosario) alternarGlosario(false); });

  // Las notas se abren con N seguida de O en menos de un segundo
  let ultimaN = 0;

  document.addEventListener('keydown', (e) => {
    if (e.target.closest('input, textarea') || (e.key === ' ' && e.target.closest('button, a'))) return;
    const k = e.key;
    if (k === 'g' || k === 'G') { alternarGlosario(); return; }
    if (!glosario.hidden) { if (k === 'Escape') alternarGlosario(false); return; }
    if (k === 'n' || k === 'N') { ultimaN = Date.now(); return; }
    if ((k === 'o' || k === 'O') && Date.now() - ultimaN < 1000) { ultimaN = 0; cuerpo.classList.toggle('con-notas'); return; }
    // El control de KDE Connect inicia con F5; aquí entra al modo presentación en lugar de recargar
    if (k === 'F5') { e.preventDefault(); if (!cuerpo.classList.contains('presentando')) alternarPresentacion(); return; }
    if (k === 'p' || k === 'P' || (k === 'Escape' && cuerpo.classList.contains('presentando'))) alternarPresentacion();
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
