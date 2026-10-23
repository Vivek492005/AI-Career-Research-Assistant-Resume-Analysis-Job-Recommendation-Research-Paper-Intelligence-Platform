/* Resume Studio demo rails (02-06): honest, labelled sample scenes
   that run the full length of their card, directly on the page
   paper. They loop only while in view and settle to their final
   state under prefers-reduced-motion. Transform/opacity/clip
   only (plus rAF-driven counters and bar widths). */
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
    new IntersectionObserver(function (es) { cb(es[0].isIntersecting); }, { threshold: 0.25 }).observe(el);
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

  /* ---------- 02 · JD match: ring, chips, then the score breakdown ---------- */
  var matchEl = document.querySelector('[data-demo="match"]');
  if (matchEl) {
    var fg = matchEl.querySelector('.dm-ring-fg');
    var scoreEl = matchEl.querySelector('[data-dm-score]');
    var tagEl = matchEl.querySelector('[data-dm-tag]');
    var chips = Array.prototype.slice.call(matchEl.querySelectorAll('.dm-chip'));
    var meters = Array.prototype.slice.call(matchEl.querySelectorAll('[data-dm-meter]'));
    var meterNums = Array.prototype.slice.call(matchEl.querySelectorAll('[data-dm-meter-num]'));
    var CIRC = 326.7, TARGET = 82, live = false;
    function setScore(v) {
      scoreEl.textContent = Math.round(v);
      fg.style.strokeDashoffset = (CIRC * (1 - Math.max(0, Math.min(100, v)) / 100)).toFixed(1);
    }
    function chipsIn() { chips.forEach(function (c) { c.classList.add('is-in'); }); }
    function chipsOut() { chips.forEach(function (c) { c.classList.remove('is-in'); }); }
    function setMeter(i, v) {
      meters[i].style.width = v + '%';
      meterNums[i].textContent = Math.round(v) + '%';
    }
    function metersReset() { meters.forEach(function (m, i) { setMeter(i, 0); }); }
    function metersFull() { meters.forEach(function (m, i) { setMeter(i, Number(m.getAttribute('data-dm-meter')) || 0); }); }
    async function matchMain(state) {
      if (live) { await wait(2000); return; }
      chipsOut(); metersReset(); setScore(0);
      await wait(550);
      for (var i = 0; i < chips.length; i++) {
        if (!state.alive || live) return;
        chips[i].classList.add('is-in');
        await wait(160);
      }
      if (!state.alive || live) return;
      await tween(1150, function (p) { setScore(TARGET * easeOut(p)); });
      for (var mi = 0; mi < meters.length; mi++) {
        if (!state.alive || live) return;
        (function (idx) {
          var target = Number(meters[idx].getAttribute('data-dm-meter')) || 0;
          tween(700, function (p) { setMeter(idx, target * easeOut(p)); });
        })(mi);
        await wait(240);
      }
      await wait(900);
      await wait(3400);
      if (live) return;
      await fadeReset(matchEl, function () { chipsOut(); metersReset(); setScore(0); });
    }
    runner(matchEl, matchMain, function () { chipsIn(); metersFull(); setScore(TARGET); });
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
        chipsIn(); metersFull();
        tween(900, function (p) { setScore(v * easeOut(p)); });
      }).observe(resultBox, { childList: true, subtree: true });
    }
  }

  /* ---------- 03 · Bullet rewriter: the pen works down two sheets ---------- */
  var bEl = document.querySelector('[data-demo="bullet"]');
  if (bEl) {
    var pen = bEl.querySelector('.dm-pen');
    var sheets = Array.prototype.slice.call(bEl.querySelectorAll('[data-sheet]'));
    var badges = Array.prototype.slice.call(bEl.querySelectorAll('.dm-badge'));
    var CLIP_SHUT = 'inset(-12% 103% -12% -3%)', CLIP_OPEN = 'inset(-12% -3% -12% -3%)';
    function strongOf(sheet) { return sheet.querySelector('[data-dm-strong]'); }
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
      /* Tip sits at (12%, 97%) of the pen box; coords are relative
         to the rail (the pen's offset parent). */
      return { x: x - 0.12 * pen.offsetWidth, y: y - 0.97 * pen.offsetHeight };
    }
    function bulletReset() {
      sheets.forEach(function (sh) {
        sh.classList.remove('is-struck', 'is-done');
        var st = strongOf(sh);
        st.getAnimations().forEach(function (a) { a.cancel(); });
        st.style.clipPath = CLIP_SHUT;
      });
      badges.forEach(function (b) { b.classList.remove('is-in'); });
      pen.getAnimations().forEach(function (a) { a.cancel(); });
      pen.style.opacity = '0';
    }
    async function writeSheet(sheet, first, state) {
      var strong = strongOf(sheet);
      sheet.classList.add('is-struck');
      await wait(850);
      if (!state.alive) return false;
      var ar = bEl.getBoundingClientRect(), tr = strong.getBoundingClientRect();
      var baseY = tr.bottom - ar.top - 3;
      var start = penTip(tr.left - ar.left + 2, baseY);
      var end = penTip(tr.right - ar.left - 2, baseY);
      if (first) { penJump(start.x, start.y - 46, -10); pen.style.opacity = '1'; }
      await penTo(start.x, start.y, 10, first ? 480 : 640);
      pen.classList.add('is-writing');
      strong.getAnimations().forEach(function (a) { a.cancel(); });
      var wipe = strong.animate([
        { clipPath: CLIP_SHUT }, { clipPath: CLIP_OPEN }
      ], { duration: 2000, easing: 'linear', fill: 'forwards' });
      var travel = penTo(end.x, end.y, 10, 2000, 'linear');
      await Promise.all([wipe.finished.catch(function () {}), travel]);
      pen.classList.remove('is-writing');
      sheet.classList.add('is-done');
      return true;
    }
    async function bulletMain(state) {
      bulletReset();
      await wait(650);
      for (var si = 0; si < sheets.length; si++) {
        if (!state.alive) return;
        var ok = await writeSheet(sheets[si], si === 0, state);
        if (!ok) return;
        await wait(250);
      }
      for (var bi = 0; bi < badges.length; bi++) { badges[bi].classList.add('is-in'); await wait(130); }
      pen.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 450, fill: 'forwards' });
      await wait(3300);
      await fadeReset(bEl, bulletReset);
    }
    if (!reduce) sheets.forEach(function (sh) { strongOf(sh).style.clipPath = CLIP_SHUT; });
    runner(bEl, bulletMain, function () {
      sheets.forEach(function (sh) {
        sh.classList.add('is-struck', 'is-done');
        strongOf(sh).style.clipPath = '';
      });
      badges.forEach(function (b) { b.classList.add('is-in'); });
    });
  }

  /* ---------- 04 · Saved versions: spotlight walks the timeline ---------- */
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
      await wait(2300);
      if (!vPaused) { vIdx = (vIdx + 1) % rows.length; showRow(vIdx); }
    }
    runner(vEl, versionsMain, function () { showRow(0); });
  }

  /* ---------- 05 · Cover letter + outreach note: two typewriters ---------- */
  var cEl = document.querySelector('[data-demo="cover"]');
  if (cEl) {
    var typeEl = cEl.querySelector('[data-dm-type]');
    var type2El = cEl.querySelector('[data-dm-type2]');
    var LINES = [
      'Subject: Application — Data Analyst Intern',
      '',
      'Dear Hiring Team,',
      'My churn-analysis project cut reporting',
      'time by 40% using Python and SQL.',
      'I would love to bring the same rigour',
      'to your data team.',
      'Warm regards, Eliza'
    ];
    var NOTE = [
      'Hi Sarah — I loved your team’s churn series.',
      'My project cut reporting time by 40%;',
      'happy to share how. — Eliza'
    ];
    async function typeInto(el, lines, state) {
      for (var li = 0; li < lines.length; li++) {
        var line = lines[li];
        for (var ci = 0; ci < line.length; ci++) {
          if (!state.alive) return false;
          el.textContent += line[ci];
          await wait(22);
        }
        if (li < lines.length - 1) { el.textContent += '\n'; await wait(line ? 240 : 90); }
      }
      return true;
    }
    async function coverMain(state) {
      typeEl.textContent = ''; type2El.textContent = '';
      cEl.classList.remove('is-note');
      await wait(550);
      var ok = await typeInto(typeEl, LINES, state);
      if (!ok) return;
      await wait(650);
      cEl.classList.add('is-note');
      ok = await typeInto(type2El, NOTE, state);
      if (!ok) return;
      await wait(3600);
      await fadeReset(cEl, function () {
        typeEl.textContent = ''; type2El.textContent = '';
        cEl.classList.remove('is-note');
      });
    }
    runner(cEl, coverMain, function () {
      typeEl.textContent = LINES.join('\n');
      type2El.textContent = NOTE.join('\n');
    });
  }

  /* ---------- 06 · LinkedIn grader: dial, headline, then the audit ---------- */
  var lEl = document.querySelector('[data-demo="linkedin"]');
  if (lEl) {
    var gradeEl = lEl.querySelector('[data-dm-grade]');
    var barEl = lEl.querySelector('[data-dm-bar]');
    var pctEl = lEl.querySelector('[data-dm-pct]');
    var headEl = lEl.querySelector('[data-dm-headline]');
    var checks = Array.prototype.slice.call(lEl.querySelectorAll('[data-dm-check]'));
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
    function checksReset() {
      checks.forEach(function (i) {
        i.style.width = '0';
        i.closest('.dm-check').classList.remove('is-in');
      });
    }
    function checksFull() {
      checks.forEach(function (i) {
        i.style.width = (Number(i.getAttribute('data-dm-check')) || 0) + '%';
        i.closest('.dm-check').classList.add('is-in');
      });
    }
    function liReset() {
      gradeEl.textContent = 'D';
      setPct(38);
      headEl.getAnimations().forEach(function (a) { a.cancel(); });
      headEl.style.clipPath = '';
      headEl.textContent = WEAK;
      checksReset();
    }
    async function liMain(state) {
      liReset();
      await wait(750);
      if (!state.alive) return;
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
      for (var ci = 0; ci < checks.length; ci++) {
        if (!state.alive) return;
        (function (bar) {
          var row = bar.closest('.dm-check');
          row.classList.add('is-in');
          var target = Number(bar.getAttribute('data-dm-check')) || 0;
          tween(600, function (p) { bar.style.width = (target * easeOut(p)) + '%'; });
        })(checks[ci]);
        await wait(300);
      }
      await wait(3400);
      await fadeReset(lEl, liReset);
    }
    runner(lEl, liMain, function () {
      gradeEl.textContent = 'A';
      setPct(92);
      headEl.textContent = STRONG;
      checksFull();
    });
  }
})();
