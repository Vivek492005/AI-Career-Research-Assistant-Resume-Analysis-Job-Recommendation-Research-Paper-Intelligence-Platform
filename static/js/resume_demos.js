/* Resume Studio demo panels (02-06): honest, labelled sample runs
   that loop while their card is in view. Transform/opacity/clip
   only. Under prefers-reduced-motion each panel settles to its
   final state and never loops. */
(function () {
  'use strict';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function tween(dur, fn) {
    return new Promise(function (res) {
      var t0 = null;
      function frame(t) {
        if (!t0) t0 = t;
        var p = Math.min(1, (t - t0) / dur);
        fn(p);
        if (p < 1) requestAnimationFrame(frame); else res();
      }
      requestAnimationFrame(frame);
    });
  }
  function easeOut(p) { return 1 - Math.pow(1 - p, 3); }
  function onView(el, cb) {
    if (!('IntersectionObserver' in window)) { cb(true); return; }
    new IntersectionObserver(function (es) { cb(es[0].isIntersecting); }, { threshold: 0.3 }).observe(el);
  }
  /* Runner: main(state) loops while the panel is in view. */
  function runner(el, main, final) {
    if (reduce) { if (final) final(); return; }
    var state = { alive: false, running: false };
    async function go() {
      if (state.running) return;
      state.running = true;
      while (state.alive) { await main(state); }
      state.running = false;
    }
    onView(el, function (v) { state.alive = v; if (v) go(); });
  }
  async function fadeReset(el, apply) {
    el.classList.add('is-resetting');
    await wait(380);
    apply();
    el.classList.remove('is-resetting');
    await wait(380);
  }

  /* ---------- 02 · JD match: ring + streaming keyword chips ---------- */
  var matchEl = document.querySelector('[data-demo="match"]');
  if (matchEl) {
    var fg = matchEl.querySelector('.dm-ring-fg');
    var scoreEl = matchEl.querySelector('[data-dm-score]');
    var tagEl = matchEl.querySelector('[data-dm-tag]');
    var chips = Array.prototype.slice.call(matchEl.querySelectorAll('.dm-chip'));
    var CIRC = 326.7, TARGET = 82, live = false;
    function setScore(v) {
      scoreEl.textContent = Math.round(v);
      fg.style.strokeDashoffset = (CIRC * (1 - Math.max(0, Math.min(100, v)) / 100)).toFixed(1);
    }
    function chipsIn() { chips.forEach(function (c) { c.classList.add('is-in'); }); }
    function chipsOut() { chips.forEach(function (c) { c.classList.remove('is-in'); }); }
    async function matchMain(state) {
      if (live) { await wait(2000); return; }
      chipsOut(); setScore(0);
      await wait(550);
      for (var i = 0; i < chips.length; i++) {
        if (!state.alive || live) return;
        chips[i].classList.add('is-in');
        await wait(160);
      }
      if (!state.alive || live) return;
      await tween(1150, function (p) { setScore(TARGET * easeOut(p)); });
      await wait(3600);
      if (live) return;
      await fadeReset(matchEl, function () { chipsOut(); setScore(0); });
    }
    runner(matchEl, matchMain, function () { chipsIn(); setScore(TARGET); });
    /* When the user runs a real match, mirror its score here. */
    var resultBox = document.getElementById('jdMatchResult');
    if (resultBox && 'MutationObserver' in window) {
      new MutationObserver(function () {
        var strong = resultBox.querySelector('.jd-ring-label strong');
        if (!strong) return;
        var v = parseInt(strong.textContent, 10);
        if (isNaN(v)) return;
        live = true;
        if (tagEl) tagEl.textContent = 'Your latest match';
        chipsIn();
        tween(900, function (p) { setScore(v * easeOut(p)); });
      }).observe(resultBox, { childList: true, subtree: true });
    }
  }

  /* ---------- 03 · Bullet rewriter: strike, pen, stronger line ---------- */
  var bEl = document.querySelector('[data-demo="bullet"]');
  if (bEl) {
    var sheet = bEl.querySelector('.dm-sheet');
    var strong = bEl.querySelector('[data-dm-strong]');
    var pen = bEl.querySelector('.dm-pen');
    var badges = Array.prototype.slice.call(bEl.querySelectorAll('.dm-badge'));
    var CLIP_SHUT = 'inset(-12% 103% -12% -3%)', CLIP_OPEN = 'inset(-12% -3% -12% -3%)';
    function penJump(x, y, rot) {
      pen.getAnimations().forEach(function (a) { a.cancel(); });
      pen.style.transform = 'translate(' + x + 'px,' + y + 'px) rotate(' + rot + 'deg)';
    }
    function penTo(x, y, rot, dur, easing) {
      var cur = pen.style.transform || 'translate(0px,0px) rotate(0deg)';
      var a = pen.animate([
        { transform: cur },
        { transform: 'translate(' + x + 'px,' + y + 'px) rotate(' + rot + 'deg)' }
      ], { duration: dur, easing: easing || 'ease-in-out', fill: 'forwards' });
      return a.finished.catch(function () {}).then(function () {
        pen.style.transform = 'translate(' + x + 'px,' + y + 'px) rotate(' + rot + 'deg)';
      });
    }
    function penTip(x, y) {
      /* Convert a desired TIP point (sheet coords) to the wrap's
         translate values: tip sits at (12%, 97%) of the pen box. */
      return { x: x - 0.12 * pen.offsetWidth, y: y - 0.97 * pen.offsetHeight };
    }
    function bulletReset() {
      sheet.classList.remove('is-struck', 'is-done');
      strong.getAnimations().forEach(function (a) { a.cancel(); });
      strong.style.clipPath = CLIP_SHUT;
      badges.forEach(function (b) { b.classList.remove('is-in'); });
      pen.getAnimations().forEach(function (a) { a.cancel(); });
      pen.style.opacity = '0';
    }
    async function bulletMain(state) {
      bulletReset();
      await wait(650);
      if (!state.alive) return;
      sheet.classList.add('is-struck');
      await wait(900);
      if (!state.alive) return;
      var sr = sheet.getBoundingClientRect(), tr = strong.getBoundingClientRect();
      var baseY = tr.bottom - sr.top - 3;
      var start = penTip(tr.left - sr.left + 2, baseY);
      var end = penTip(tr.right - sr.left - 2, baseY);
      penJump(start.x, start.y - 46, -10);
      pen.style.opacity = '1';
      await penTo(start.x, start.y, 10, 480);
      pen.classList.add('is-writing');
      strong.getAnimations().forEach(function (a) { a.cancel(); });
      var wipe = strong.animate([
        { clipPath: CLIP_SHUT }, { clipPath: CLIP_OPEN }
      ], { duration: 2100, easing: 'linear', fill: 'forwards' });
      var travel = penTo(end.x, end.y, 10, 2100, 'linear');
      await Promise.all([wipe.finished.catch(function () {}), travel]);
      pen.classList.remove('is-writing');
      sheet.classList.add('is-done');
      for (var i = 0; i < badges.length; i++) { badges[i].classList.add('is-in'); await wait(130); }
      pen.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 450, fill: 'forwards' });
      await wait(3300);
      await fadeReset(bEl, bulletReset);
    }
    if (!reduce) strong.style.clipPath = CLIP_SHUT;
    runner(bEl, bulletMain, function () {
      sheet.classList.add('is-struck', 'is-done');
      strong.style.clipPath = '';
      badges.forEach(function (b) { b.classList.add('is-in'); });
    });
  }

  /* ---------- 04 · Saved versions: spotlight cycles the rows ---------- */
  var vEl = document.querySelector('[data-demo="versions"]');
  if (vEl) {
    var stack = vEl.querySelector('[data-dm-stack]');
    var rows = Array.prototype.slice.call(vEl.querySelectorAll('.dm-vs'));
    var vIdx = 0, vPaused = false;
    function showRow(i) {
      rows.forEach(function (r, j) { r.classList.toggle('is-active', i === j); });
    }
    showRow(0);
    stack.addEventListener('mouseenter', function () { vPaused = true; });
    stack.addEventListener('mouseleave', function () { vPaused = false; });
    async function versionsMain(state) {
      await wait(2600);
      if (!vPaused) { vIdx = (vIdx + 1) % rows.length; showRow(vIdx); }
    }
    runner(vEl, versionsMain, function () { showRow(0); });
  }

  /* ---------- 05 · Cover letter: typewriter ---------- */
  var cEl = document.querySelector('[data-demo="cover"]');
  if (cEl) {
    var typeEl = cEl.querySelector('[data-dm-type]');
    var LINES = [
      'Dear Hiring Team,',
      'My churn-analysis project cut reporting',
      'time by 40% using Python and SQL.',
      'I would love to bring the same rigour',
      'to your data team.',
      'Warm regards, Eliza'
    ];
    var FULL = LINES.join('\n');
    async function coverMain(state) {
      typeEl.textContent = '';
      await wait(550);
      for (var li = 0; li < LINES.length; li++) {
        var line = LINES[li];
        for (var ci = 0; ci < line.length; ci++) {
          if (!state.alive) return;
          typeEl.textContent += line[ci];
          await wait(24);
        }
        if (li < LINES.length - 1) { typeEl.textContent += '\n'; await wait(280); }
      }
      await wait(3400);
      await fadeReset(cEl, function () { typeEl.textContent = ''; });
    }
    runner(cEl, coverMain, function () { typeEl.textContent = FULL; });
  }

  /* ---------- 06 · LinkedIn grader: grade dial + headline rewrite ---------- */
  var lEl = document.querySelector('[data-demo="linkedin"]');
  if (lEl) {
    var gradeEl = lEl.querySelector('[data-dm-grade]');
    var barEl = lEl.querySelector('[data-dm-bar]');
    var pctEl = lEl.querySelector('[data-dm-pct]');
    var headEl = lEl.querySelector('[data-dm-headline]');
    var WEAK = 'Student at University of Washington';
    var STRONG = 'CS Senior · Data Science Intern · Python, SQL, ML';
    var SHUT = 'inset(-12% 103% -12% -3%)', OPEN = 'inset(-12% -3% -12% -3%)';
    function setGrade(g) {
      if (gradeEl.textContent === g) return;
      gradeEl.textContent = g;
      gradeEl.classList.remove('is-pop');
      void gradeEl.offsetWidth;
      gradeEl.classList.add('is-pop');
    }
    function setPct(v) {
      pctEl.textContent = Math.round(v) + '%';
      barEl.style.width = v + '%';
    }
    function liReset() {
      gradeEl.textContent = 'D';
      setPct(38);
      headEl.getAnimations().forEach(function (a) { a.cancel(); });
      headEl.style.clipPath = '';
      headEl.textContent = WEAK;
    }
    async function liMain(state) {
      liReset();
      await wait(750);
      if (!state.alive) return;
      /* Headline: wipe shut, swap, wipe open. */
      var shut = headEl.animate([{ clipPath: OPEN }, { clipPath: SHUT }], { duration: 480, easing: 'ease-in', fill: 'forwards' });
      await shut.finished.catch(function () {});
      headEl.textContent = STRONG;
      headEl.getAnimations().forEach(function (a) { a.cancel(); });
      var open = headEl.animate([{ clipPath: SHUT }, { clipPath: OPEN }], { duration: 750, easing: 'ease-out', fill: 'forwards' });
      open.finished.catch(function () {});
      await tween(1500, function (p) {
        var v = 38 + (92 - 38) * easeOut(p);
        setPct(v);
        if (v >= 88) setGrade('A'); else if (v >= 72) setGrade('B'); else if (v >= 54) setGrade('C');
      });
      await wait(3400);
      await fadeReset(lEl, liReset);
    }
    runner(lEl, liMain, function () {
      gradeEl.textContent = 'A';
      setPct(92);
      headEl.textContent = STRONG;
    });
  }
})();
