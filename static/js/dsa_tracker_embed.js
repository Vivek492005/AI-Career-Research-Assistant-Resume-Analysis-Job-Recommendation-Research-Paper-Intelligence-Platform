/* Embedded A2Z tracker on /dsa: refresh the numbers from
   /api/dsa/progress when the tab becomes visible again, so marks
   made in another tab (or on a problem page) appear without a
   manual reload. Server-rendered values are the initial paint. */
(function () {
  "use strict";
  var section = document.getElementById("progress-tracker");
  if (!section) return;

  function setText(sel, text) {
    var n = section.querySelector(sel);
    if (n) n.textContent = text;
  }

  function refresh() {
    fetch("/api/dsa/progress", { headers: { "Accept": "application/json" },
                                 cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !d.a2z) return;
        var a = d.a2z;
        setText('[data-stat="solved"]', a.solved + "/" + a.total);
        setText('[data-stat="inprogress"]', String(a.attempted + a.stuck));
        setText('[data-stat="stuck"]', String(a.stuck));
        setText('[data-stat="notstarted"]', String(a.total - a.tracked));
        var gauge = document.getElementById("dt-gauge");
        if (gauge) {
          gauge.setAttribute("data-pct", a.pct);
          if (gauge._lqApi) gauge._lqApi.set(a.pct, "Solved");
        }
        (a.by_difficulty || []).forEach(function (df) {
          var row = section.querySelector('[data-diff="' + df.difficulty + '"]');
          if (!row) return;
          var fill = row.querySelector(".dt-fill");
          if (fill) fill.style.width = df.pct + "%";
          var num = row.querySelector(".dt-num");
          if (num) num.textContent = df.solved + "/" + df.total + " · " + df.pct + "%";
        });
        (a.by_step || []).forEach(function (s) {
          var mod = section.querySelector('[data-step="' + s.step + '"]');
          if (!mod) return;
          var fill = mod.querySelector(".dt-fill");
          if (fill) fill.style.width = s.pct + "%";
          var num = mod.querySelector(".dt-mod-num");
          if (num) num.textContent = s.solved + "/" + s.total + " · " + s.pct + "%";
        });
        var classic = document.getElementById("classic-strong");
        if (classic && d.classic) {
          classic.textContent = d.classic.solved + "/" + d.classic.total +
            " solved (" + d.classic.pct + "%)";
        }
      })
      .catch(function () {});
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) refresh();
  });
  window.addEventListener("focus", refresh);
  // Belt and braces: focus/visibility events are not fired by every
  // browser in every tab-switch path, so also poll gently while the
  // page is visible. The payload is a tiny aggregate JSON.
  setInterval(function () { if (!document.hidden) refresh(); }, 12000);
  // One refresh shortly after load covers marks saved just before
  // arriving here (e.g. from a problem page in the same tab flow).
  setTimeout(refresh, 600);
})();
