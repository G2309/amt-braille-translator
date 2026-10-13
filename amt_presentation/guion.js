// Arma el guion a partir de las notas del orador de la presentación, agrupado por parte y con su tiempo
(async () => {
  const minutos = Number(new URLSearchParams(location.search).get('min')) || 40;
  const contenedor = document.getElementById('partes');
  const indice = document.querySelector('.indice ol');
  const html = await (await fetch('./')).text();
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const secciones = [...doc.querySelectorAll('.slide[data-peso]')];
  const pesoTotal = secciones.reduce((a, s) => a + Number(s.dataset.peso), 0);
  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;
  const partes = [];
  for (const s of secciones) {
    const nombre = s.dataset.parte;
    if (!partes.length || partes.at(-1).nombre !== nombre) partes.push({ nombre, secciones: [] });
    partes.at(-1).secciones.push(s);
  }
  contenedor.textContent = '';
  let reloj = 0;
  partes.forEach((parte, n) => {
    const id = `parte-${n + 1}`;
    const duracion = parte.secciones.reduce((a, s) => a + (Number(s.dataset.peso) / pesoTotal) * minutos * 60, 0);
    const bloque = document.createElement('section');
    bloque.className = 'parte';
    bloque.id = id;
    bloque.innerHTML = `<h2>${n + 1}. ${parte.nombre}</h2><p class="tiempo">De ${fmt(reloj)} a ${fmt(reloj + duracion)} · ${fmt(duracion)} en total</p>`;
    parte.secciones.forEach((s) => {
      const notas = s.querySelector('.notas');
      const art = document.createElement('article');
      art.innerHTML = notas ? notas.innerHTML : '';
      const primero = art.querySelector('p:first-child');
      if (primero && primero.querySelector('b')) primero.outerHTML = `<h3>${primero.textContent}</h3>`;
      bloque.append(art);
    });
    contenedor.append(bloque);
    indice.insertAdjacentHTML('beforeend', `<li><a href="#${id}">${parte.nombre}</a> <span>${fmt(reloj)}</span></li>`);
    reloj += duracion;
  });
  const respaldo = [...doc.querySelectorAll('.slide.respaldo')];
  if (respaldo.length) {
    const bloque = document.createElement('section');
    bloque.className = 'parte';
    bloque.id = 'respuestas';
    bloque.innerHTML = '<h2>Respuestas para la ronda de preguntas</h2><p class="tiempo">Se muestran con la tecla R</p>';
    respaldo.forEach((s) => {
      const art = document.createElement('article');
      art.innerHTML = s.querySelector('.notas')?.innerHTML || '';
      const primero = art.querySelector('p:first-child');
      if (primero && primero.querySelector('b')) primero.outerHTML = `<h3>${primero.textContent}</h3>`;
      bloque.append(art);
    });
    contenedor.append(bloque);
    indice.insertAdjacentHTML('beforeend', '<li><a href="#respuestas">Preguntas del jurado</a></li>');
  }
})();
