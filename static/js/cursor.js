/* Study-Buddy cursor FX: dot+ring cursor, dark-page spotlight glow,
   magnetic CTAs, hover labels, 3D tilt cards. Runs only on pointer-fine
   devices without reduced-motion; the native cursor is kept throughout. */
(function () {
  'use strict';
  if (!window.matchMedia) return;
  if (!matchMedia('(pointer: fine)').matches) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var script = document.currentScript;
  if (script && script.src) {
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = script.src.replace(/\/js\/cursor\.js(\?.*)?$/, '/css/cursor.css');
    document.head.appendChild(link);
  }

  function make(cls) {
    var d = document.createElement('div');
    d.className = cls;
    d.setAttribute('aria-hidden', 'true');
    document.body.appendChild(d);
    return d;
  }
  var glow = make('sb-cursor-glow');
  var ring = make('sb-cursor-ring');
  var label = document.createElement('span');
  label.className = 'sb-cursor-label';
  ring.appendChild(label);
  var dot = make('sb-cursor-dot');

  /* Spotlight only makes sense on dark surfaces. */
  try {
    var bgc = getComputedStyle(document.body).backgroundColor || '';
    var mm = /(\d+)[, ]+(\d+)[, ]+(\d+)/.exec(bgc);
    if (mm && (0.2126 * +mm[1] + 0.7152 * +mm[2] + 0.0722 * +mm[3]) / 255 < 0.4) {
      glow.classList.add('on');
    }
  } catch (e) { /* no glow */ }

  var tx = window.innerWidth / 2, ty = window.innerHeight / 2;
  var rx = tx, ry = ty, gx = tx, gy = ty, shown = false;
  document.addEventListener('mousemove', function (e) {
    tx = e.clientX; ty = e.clientY;
    if (!shown) { shown = true; document.body.classList.add('sb-cursor-on'); rx = tx; ry = ty; gx = tx; gy = ty; }
    dot.style.transform = 'translate(' + tx + 'px,' + ty + 'px) translate(-50%,-50%)';
  }, { passive: true });
  document.addEventListener('mouseleave', function () {
    shown = false;
    document.body.classList.remove('sb-cursor-on');
  });
  (function loop() {
    rx += (tx - rx) * 0.2; ry += (ty - ry) * 0.2;
    gx += (tx - gx) * 0.07; gy += (ty - gy) * 0.07;
    ring.style.transform = 'translate(' + rx + 'px,' + ry + 'px) translate(-50%,-50%)';
    glow.style.transform = 'translate(' + gx + 'px,' + gy + 'px) translate(-50%,-50%)';
    requestAnimationFrame(loop);
  })();

  var INTERACTIVE = 'a, button, [role="button"], input, select, textarea, label, summary';
  var LABELS = [
    ['.sb-tool', 'Open →'],
    ['.sb-dash-side a', 'Open →'],
    ['.sb-dsa-wrap a[href*="/dsa/"]', 'Solve →'],
    ['.feature-card', 'Explore →']
  ];
  function labelFor(t) {
    if (!t || !t.closest) return '';
    var explicit = t.closest('[data-cursor-label]');
    if (explicit) return explicit.getAttribute('data-cursor-label');
    for (var i = 0; i < LABELS.length; i++) {
      if (t.closest(LABELS[i][0])) return LABELS[i][1];
    }
    return '';
  }
  document.addEventListener('mouseover', function (e) {
    var lab = labelFor(e.target);
    if (lab) {
      label.textContent = lab;
      ring.classList.add('is-label');
      ring.classList.remove('is-hover');
      return;
    }
    ring.classList.remove('is-label');
    if (e.target.closest && e.target.closest(INTERACTIVE)) ring.classList.add('is-hover');
    else ring.classList.remove('is-hover');
  }, { passive: true });

  /* Homepage hero parallax: figure, brush, notes, card and headline drift
     at different depths with the pointer (body.sb-editorial only). */
  if (document.body.classList.contains('sb-editorial')) {
    var hero = document.querySelector('.sb-hero');
    if (hero) {
      var layers = [
        [hero.querySelector('.sb-hero-visual'), 10, 8],
        [hero.querySelector('.sb-brush'), -6, -5],
        [hero.querySelector('.sb-note--a'), 15, 11],
        [hero.querySelector('.sb-note--b'), 18, 13],
        [hero.querySelector('.sb-hero-card'), 7, 6],
        [hero.querySelector('.sb-display'), 4, 3]
      ].filter(function (l) { return l[0]; });
      var pnx = 0, pny = 0, pcx = 0, pcy = 0;
      hero.addEventListener('mousemove', function (e) {
        var r = hero.getBoundingClientRect();
        pnx = ((e.clientX - r.left) / r.width - 0.5) * 2;
        pny = ((e.clientY - r.top) / r.height - 0.5) * 2;
      });
      hero.addEventListener('mouseleave', function () { pnx = 0; pny = 0; });
      (function ploop() {
        pcx += (pnx - pcx) * 0.06; pcy += (pny - pcy) * 0.06;
        for (var i = 0; i < layers.length; i++) {
          layers[i][0].style.translate = (pcx * layers[i][1]).toFixed(1) + 'px ' + (pcy * layers[i][2]).toFixed(1) + 'px';
        }
        requestAnimationFrame(ploop);
      })();
    }
  }

  /* Magnetic CTAs: drift toward the pointer, snap back on leave. */
  document.querySelectorAll('a.sb-btn, .b-btn--primary, .sb-hero-card').forEach(function (elm) {
    elm.addEventListener('mousemove', function (e) {
      var r = elm.getBoundingClientRect();
      var x = (e.clientX - r.left - r.width / 2) / r.width;
      var y = (e.clientY - r.top - r.height / 2) / r.height;
      elm.style.transform = 'translate(' + (x * 10).toFixed(1) + 'px,' + (y * 8).toFixed(1) + 'px)';
    });
    elm.addEventListener('mouseleave', function () { elm.style.transform = ''; });
  });

  /* 3D tilt + shine on showcase cards. */
  document.querySelectorAll('.sb-tool, .sb-step, .feature-card, [data-tilt]').forEach(function (card) {
    card.classList.add('sb-tilt');
    card.addEventListener('mousemove', function (e) {
      var r = card.getBoundingClientRect();
      var px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
      card.style.transform = 'perspective(900px) rotateX(' + ((0.5 - py) * 7).toFixed(2) + 'deg) rotateY(' + ((px - 0.5) * 7).toFixed(2) + 'deg)';
      card.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
      card.style.setProperty('--my', (py * 100).toFixed(1) + '%');
    });
    card.addEventListener('mouseleave', function () { card.style.transform = ''; });
  });
})();
