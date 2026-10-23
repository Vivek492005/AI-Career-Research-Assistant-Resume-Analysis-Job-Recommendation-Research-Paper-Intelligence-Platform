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

  /* Headline word replay: hovering a masked display line replays its
     rise-up reveal (exit up, re-appear from below). Restartable. */
  document.querySelectorAll('.sb-mask').forEach(function (mask) {
    var inner = mask.querySelector('span');
    if (!inner) return;
    mask.addEventListener('mouseenter', function () {
      inner.classList.remove('sb-replay');
      void inner.offsetWidth;
      inner.classList.add('sb-replay');
    });
    inner.addEventListener('animationend', function () {
      inner.classList.remove('sb-replay');
    });
  });

  /* Hero photo "generation" reveal: on hover the photo vanishes to
     blank, then materialises like an AI image generating — huge pixel
     blocks that refine step by step into the sharp full image. The
     real <img> hides underneath while the canvas performs, so there
     is no double-image muddiness. */
  var heroVisual = document.querySelector('.sb-hero-visual');
  var heroImg = heroVisual ? heroVisual.querySelector('.sb-hero-photo') : null;
  if (heroVisual && heroImg) {
    var pxCanvas = document.createElement('canvas');
    pxCanvas.className = 'sb-pixel-canvas';
    pxCanvas.setAttribute('aria-hidden', 'true');
    heroVisual.appendChild(pxCanvas);
    var pxBusy = false;
    function playGeneration() {
      if (pxBusy || !heroImg.complete || !heroImg.naturalWidth) return;
      pxBusy = true;
      var box = heroImg.getBoundingClientRect();
      var W = Math.max(2, Math.round(box.width)), H = Math.max(2, Math.round(box.height));
      pxCanvas.width = W; pxCanvas.height = H;
      var ctx = pxCanvas.getContext('2d');
      var scale = Math.min(W / heroImg.naturalWidth, H / heroImg.naturalHeight);
      var dw = heroImg.naturalWidth * scale, dh = heroImg.naturalHeight * scale;
      var dx = (W - dw) * 0.58, dy = H - dh;
      var small = document.createElement('canvas');
      var sctx = small.getContext('2d');
      var steps = [[80, 70], [48, 60], [28, 55], [16, 50], [8, 45], [3, 40]];
      var i = 0;
      /* Blank first: hide the photo, show the empty canvas. */
      heroImg.style.opacity = '0';
      ctx.clearRect(0, 0, W, H);
      pxCanvas.classList.remove('off');
      pxCanvas.classList.add('on');
      function drawPixels(size) {
        var w2 = Math.max(1, Math.round(dw / size)), h2 = Math.max(1, Math.round(dh / size));
        small.width = w2; small.height = h2;
        sctx.drawImage(heroImg, 0, 0, w2, h2);
        ctx.imageSmoothingEnabled = false;
        ctx.clearRect(0, 0, W, H);
        ctx.drawImage(small, 0, 0, w2, h2, dx, dy, dw, dh);
      }
      function step() {
        if (i < steps.length) {
          drawPixels(steps[i][0]);
          var wait = steps[i][1];
          i++;
          setTimeout(step, wait);
        } else {
          /* Sharp final frame on the canvas, then cross-fade back to
             the real image (identical rendering, invisible swap). */
          ctx.imageSmoothingEnabled = true;
          ctx.clearRect(0, 0, W, H);
          ctx.drawImage(heroImg, dx, dy, dw, dh);
          heroImg.style.opacity = '';
          pxCanvas.classList.add('off');
          pxCanvas.classList.remove('on');
          setTimeout(function () { pxBusy = false; }, 150);
        }
      }
      setTimeout(step, 60);
    }
    heroVisual.addEventListener('mouseenter', playGeneration);
    /* Auto-play once when the page opens, like the headline reveal on
       the left: shortly after load, if the hero is on screen. */
    function autoPlay() {
      var r = heroVisual.getBoundingClientRect();
      if (r.bottom > 0 && r.top < window.innerHeight) playGeneration();
    }
    if (heroImg.complete && heroImg.naturalWidth) setTimeout(autoPlay, 750);
    else heroImg.addEventListener('load', function () { setTimeout(autoPlay, 750); });
  }

  /* Outline stage: a blocky theme character runs in and places the
     slogan block by block (arm swing + block pop + dust puffs), then
     jumps and poofs away. Loops while the band is on screen. */
  var band = document.querySelector('.sb-outline-band');
  var stage = band ? band.querySelector('.sb-outline-stage') : null;
  var charEl = band ? band.querySelector('.sb-char') : null;
  var blks = band ? Array.prototype.slice.call(band.querySelectorAll('.sb-blk')) : [];
  if (band && stage && charEl && blks.length) {
    var playing = false, inView = false;
    function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    function puff(x, y, cls) {
      for (var i = 0; i < 7; i++) {
        var p = document.createElement('i');
        p.className = 'sb-puff' + (cls ? ' ' + cls : '');
        p.style.left = x + 'px'; p.style.top = y + 'px';
        stage.appendChild(p);
        var ang = (i / 7) * Math.PI * 2, dist = 16 + (i % 3) * 9;
        var anim = p.animate([
          { transform: 'translate(0,0) scale(1)', opacity: 1 },
          { transform: 'translate(' + (Math.cos(ang) * dist).toFixed(1) + 'px,' + (Math.sin(ang) * dist - 12).toFixed(1) + 'px) scale(0.4)', opacity: 0 }
        ], { duration: 480, easing: 'ease-out' });
        anim.onfinish = (function (el) { return function () { el.remove(); }; })(p);
      }
    }
    function moveCharTo(x, speed) {
      var cur = parseFloat(charEl.dataset.x || '-90');
      var dur = Math.max(80, Math.abs(x - cur) / speed);
      charEl.dataset.x = x;
      charEl.classList.add('is-running');
      charEl.style.transition = 'transform ' + dur + 'ms linear';
      charEl.style.transform = 'translateX(' + x + 'px)';
      return wait(dur).then(function () { charEl.classList.remove('is-running'); });
    }
    function stageCenterX(el) {
      var sr = stage.getBoundingClientRect(), r = el.getBoundingClientRect();
      return r.left - sr.left + r.width / 2 - 23;
    }
    function stageBaseY(el) {
      var sr = stage.getBoundingClientRect(), r = el.getBoundingClientRect();
      return r.bottom - sr.top - 8;
    }
    async function playOnce() {
      band.classList.remove('is-clearing');
      band.classList.add('is-live');
      blks.forEach(function (b) { b.classList.remove('is-placed'); });
      charEl.hidden = false;
      charEl.style.opacity = '1';
      charEl.style.transition = 'none';
      charEl.style.transform = 'translateX(-90px)';
      charEl.dataset.x = -90;
      await wait(80);
      for (var i = 0; i < blks.length; i++) {
        await moveCharTo(stageCenterX(blks[i]), 0.55);
        charEl.classList.add('is-placing');
        await wait(150);
        blks[i].classList.add('is-placed');
        puff(stageCenterX(blks[i]) + 14, stageBaseY(blks[i]), i === 1 ? 'sb-puff--blue' : '');
        await wait(240);
        charEl.classList.remove('is-placing');
      }
      await moveCharTo(stageCenterX(blks[blks.length - 1]) + 130, 0.7);
      charEl.classList.add('is-jumping');
      await wait(210);
      var sr2 = stage.getBoundingClientRect();
      puff(parseFloat(charEl.dataset.x) + 8, sr2.height - 62, 'sb-puff--ink');
      puff(parseFloat(charEl.dataset.x) + 22, sr2.height - 30, '');
      charEl.style.opacity = '0';
      charEl.classList.remove('is-jumping');
      await wait(450);
      charEl.hidden = true;
      await wait(3600);
      band.classList.add('is-clearing');
      await wait(650);
      band.classList.remove('is-live');
    }
    async function stageLoop() {
      if (playing) return;
      playing = true;
      while (inView) { await playOnce(); await wait(400); }
      playing = false;
    }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        inView = entries[0].isIntersecting;
        if (inView) stageLoop();
      }, { threshold: 0.3 }).observe(band);
    } else { inView = true; stageLoop(); }
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
    var title = card.querySelector('.sb-tool-title');
    if (title) {
      card.addEventListener('mouseenter', function () {
        title.classList.remove('sb-title-replay');
        void title.offsetWidth;
        title.classList.add('sb-title-replay');
      });
      title.addEventListener('animationend', function () {
        title.classList.remove('sb-title-replay');
      });
    }
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
