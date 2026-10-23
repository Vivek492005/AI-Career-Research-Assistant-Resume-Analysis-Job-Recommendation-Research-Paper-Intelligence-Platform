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

  /* "Generation" reveal: the photo vanishes to blank, then
     materialises like an AI image generating — huge pixel blocks
     that refine step by step into the sharp full image. The real
     <img> hides underneath while the canvas performs, so there is
     no double-image muddiness. Used by the homepage hero figure
     (contain fit, bottom-anchored) and by any [data-gen-reveal]
     visual (cover fit, full colour). */
  function attachGeneration(visual, img, fit) {
    var pxCanvas = document.createElement('canvas');
    pxCanvas.className = 'sb-pixel-canvas';
    pxCanvas.setAttribute('aria-hidden', 'true');
    visual.appendChild(pxCanvas);
    var pxBusy = false;
    function playGeneration() {
      if (pxBusy || !img.complete || !img.naturalWidth) return;
      pxBusy = true;
      var box = img.getBoundingClientRect();
      var W = Math.max(2, Math.round(box.width)), H = Math.max(2, Math.round(box.height));
      pxCanvas.width = W; pxCanvas.height = H;
      var ctx = pxCanvas.getContext('2d');
      var f = fit(W, H, img);
      var dx = f[0], dy = f[1], dw = f[2], dh = f[3];
      var small = document.createElement('canvas');
      var sctx = small.getContext('2d');
      var steps = [[80, 70], [48, 60], [28, 55], [16, 50], [8, 45], [3, 40]];
      var i = 0;
      /* Blank first: hide the photo, show the empty canvas. */
      img.style.opacity = '0';
      ctx.clearRect(0, 0, W, H);
      pxCanvas.classList.remove('off');
      pxCanvas.classList.add('on');
      function drawPixels(size) {
        var w2 = Math.max(1, Math.round(dw / size)), h2 = Math.max(1, Math.round(dh / size));
        small.width = w2; small.height = h2;
        sctx.drawImage(img, 0, 0, w2, h2);
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
          ctx.drawImage(img, dx, dy, dw, dh);
          img.style.opacity = '';
          pxCanvas.classList.add('off');
          pxCanvas.classList.remove('on');
          setTimeout(function () { pxBusy = false; }, 150);
        }
      }
      setTimeout(step, 60);
    }
    visual.addEventListener('mouseenter', playGeneration);
    /* Auto-play once when the page opens, like the headline reveal:
       shortly after load, if the visual is on screen. */
    function autoPlay() {
      var r = visual.getBoundingClientRect();
      if (r.bottom > 0 && r.top < window.innerHeight) playGeneration();
    }
    if (img.complete && img.naturalWidth) setTimeout(autoPlay, 750);
    else img.addEventListener('load', function () { setTimeout(autoPlay, 750); });
  }
  var heroVisual = document.querySelector('.sb-hero-visual');
  var heroImg = heroVisual ? heroVisual.querySelector('.sb-hero-photo') : null;
  if (heroVisual && heroImg) {
    attachGeneration(heroVisual, heroImg, function (W, H, img) {
      var scale = Math.min(W / img.naturalWidth, H / img.naturalHeight);
      var dw = img.naturalWidth * scale, dh = img.naturalHeight * scale;
      return [(W - dw) * 0.58, H - dh, dw, dh];
    });
  }
  document.querySelectorAll('[data-gen-reveal]').forEach(function (visual) {
    var img = visual.querySelector('img');
    if (!img) return;
    attachGeneration(visual, img, function (W, H, im) {
      var scale = Math.max(W / im.naturalWidth, H / im.naturalHeight);
      var dw = im.naturalWidth * scale, dh = im.naturalHeight * scale;
      return [(W - dw) / 2, (H - dh) / 2, dw, dh];
    });
  });

  /* Resume visual: no pixel reveal here — instead the photo's blue
     pen comes alive. It rests at the top of the resume photo, glides
     down to the wide band under the intro and hand-writes the
     cursive slogan across it left to right while the text wipes in
     under its tip, then flies back up to rest on the photo. Loops
     while the intro is in view; reduced-motion users simply see
     the photo and the written line. */
  var intro = document.querySelector('.sb-work-intro--split');
  var rVisual = intro ? intro.querySelector('.sb-resume-visual') : null;
  var rPhoto = intro ? intro.querySelector('.sb-resume-photo') : null;
  var rWrap = intro ? intro.querySelector('.sb-pen-wrap') : null;
  var rText = intro ? intro.querySelector('.sb-write-text') : null;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (intro && rVisual && rPhoto && rWrap && rText && !reduceMotion) {
    var penPos = null, writePlaying = false, writeInView = false;
    function wWait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    /* Move the pen so its TIP lands on section-point (tx, ty). The
       pen image's tip sits at (12%, 97%) of its box and the wrap's
       rotation origin is that same point, so rotation never moves
       the tip. */
    function penTo(tx, ty, rot, dur, easing) {
      var pw = rWrap.offsetWidth, ph = rWrap.offsetHeight;
      var to = { x: tx - 0.12 * pw, y: ty - 0.97 * ph, rot: rot };
      var from = penPos || to;
      penPos = to;
      var a = rWrap.animate([
        { transform: 'translate(' + from.x + 'px,' + from.y + 'px) rotate(' + from.rot + 'deg)' },
        { transform: 'translate(' + to.x + 'px,' + to.y + 'px) rotate(' + to.rot + 'deg)' }
      ], { duration: dur, easing: easing || 'ease-in-out', fill: 'forwards' });
      return a.finished.catch(function () {});
    }
    function secRect() { return intro.getBoundingClientRect(); }
    function linePoints() {
      var sr = secRect(), tr = rText.getBoundingClientRect();
      return {
        startX: tr.left - sr.left + 8,
        endX: tr.right - sr.left - 8,
        y: tr.bottom - sr.top - tr.height * 0.16
      };
    }
    /* Resting point: the pen lies flat along the top of the resume
       photo (rotated ~58deg from its natural diagonal, so it reads
       as lying on the desk above the sheet), tip at the left. */
    function restPoint() {
      var sr = secRect(), pr = rPhoto.getBoundingClientRect();
      return {
        x: pr.left - sr.left + pr.width * 0.56,
        y: pr.top - sr.top + pr.height * 0.14
      };
    }
    function wipeText(dur) {
      /* Cancel any finished fill-forwards animation first: a stale
         fade left at opacity 0 would otherwise keep overriding the
         inline opacity and the text would never reappear (the
         second-loop bug). */
      rText.getAnimations().forEach(function (a) { a.cancel(); });
      rText.style.opacity = '1';
      var a = rText.animate([
        { clipPath: 'inset(-12% 103% -12% -3%)' },
        { clipPath: 'inset(-12% -3% -12% -3%)' }
      ], { duration: dur, easing: 'linear', fill: 'forwards' });
      return a.finished.catch(function () {});
    }
    function fadeText(dur) {
      rText.getAnimations().forEach(function (a) { a.cancel(); });
      rText.style.opacity = '1';
      var a = rText.animate([{ opacity: 1 }, { opacity: 0 }], { duration: dur, easing: 'ease', fill: 'forwards' });
      return a.finished.catch(function () {});
    }
    async function writeOnce() {
      var rest = restPoint();
      /* Start from rest on the photo, glide down to the line. */
      await penTo(rest.x, rest.y, 58, 10, 'linear');
      await wWait(400);
      var p = linePoints();
      await penTo(p.startX, p.y, 8, 950);
      /* Write across the whole band while the text wipes in. */
      rWrap.classList.add('is-writing');
      var travel = penTo(p.endX, p.y, 8, 3300, 'linear');
      var wipe = wipeText(3300);
      await Promise.all([travel, wipe]);
      rWrap.classList.remove('is-writing');
      await wWait(250);
      /* Finished: fly back up to rest on the photo. */
      var rest2 = restPoint();
      await penTo(rest2.x, rest2.y, 58, 950);
      await wWait(3200);
      await fadeText(500);
      await wWait(450);
    }
    async function writeLoop() {
      if (writePlaying) return;
      writePlaying = true;
      intro.classList.add('sb-write-live');
      while (writeInView) { await writeOnce(); }
      writePlaying = false;
    }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        writeInView = entries[0].isIntersecting;
        if (writeInView) {
          rVisual.classList.add('sb-photo-in');
          writeLoop();
        }
      }, { threshold: 0.25 }).observe(intro);
    } else {
      writeInView = true;
      rVisual.classList.add('sb-photo-in');
      writeLoop();
    }
  }

  /* Outline stage: the slogan's letters stream in one after another
     at a steady place-rate (~7/sec) with the solid block-pop, then
     settle to outline; the band dwells, clears and loops while in
     view. Without JS (or reduced motion) the slogan simply shows. */
  var band = document.querySelector('.sb-outline-band');
  var stage = band ? band.querySelector('.sb-outline-stage') : null;
  var blks = band ? Array.prototype.slice.call(band.querySelectorAll('.sb-blk')) : [];
  if (band && stage && blks.length) {
    var playing = false, inView = false;
    function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    function puff(x, y, cls, n, size) {
      for (var i = 0; i < n; i++) {
        var p = document.createElement('i');
        p.className = 'sb-puff' + (cls ? ' ' + cls : '');
        p.style.width = size + 'px'; p.style.height = size + 'px';
        p.style.left = x + 'px'; p.style.top = y + 'px';
        stage.appendChild(p);
        var ang = (i / n) * Math.PI * 2 + 0.4, dist = 18 + (i % 3) * 11;
        var anim = p.animate([
          { transform: 'translate(0,0) scale(1)', opacity: 1 },
          { transform: 'translate(' + (Math.cos(ang) * dist).toFixed(1) + 'px,' + (Math.sin(ang) * dist - 14).toFixed(1) + 'px) scale(0.35)', opacity: 0 }
        ], { duration: 500, easing: 'ease-out' });
        anim.onfinish = (function (el) { return function () { el.remove(); }; })(p);
      }
    }
    function relRect(el) {
      var sr = stage.getBoundingClientRect(), r = el.getBoundingClientRect();
      return { left: r.left - sr.left, top: r.top - sr.top, right: r.right - sr.left, bottom: r.bottom - sr.top, width: r.width, height: r.height };
    }
    async function playOnce() {
      band.classList.remove('is-clearing');
      band.classList.add('is-live');
      blks.forEach(function (b) { b.classList.remove('is-placed'); });
      await wait(200);
      for (var i = 0; i < blks.length; i++) {
        blks[i].classList.add('is-placed');
        var r = relRect(blks[i]);
        puff(r.left + r.width / 2, r.bottom - 4, blks[i].classList.contains('sb-blk-arrow') ? 'sb-puff--blue' : '', 2, 6);
        await wait(120);
      }
      await wait(3800);
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
