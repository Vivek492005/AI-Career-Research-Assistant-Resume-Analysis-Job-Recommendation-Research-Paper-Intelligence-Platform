/* Resume results interactivity: expandable breakdown rows, live
   projected score from the fix checklist (also moves the score ring),
   per-bullet rewrites, and inline JD matching. No score is ever
   re-computed here from edited text — the projection only sums the
   checklist's server-side point estimates. */
(function () {
    'use strict';

    function csrfHeaders() {
        var headers = { 'Content-Type': 'application/json' };
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) headers['X-CSRFToken'] = meta.getAttribute('content');
        return headers;
    }

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /* ---- Expandable breakdown rows ---- */
    document.querySelectorAll('.breakdown-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var item = btn.closest('.breakdown-item');
            var more = item ? item.querySelector('.breakdown-more') : null;
            if (!more) return;
            var open = more.hasAttribute('hidden');
            if (open) { more.removeAttribute('hidden'); } else { more.setAttribute('hidden', ''); }
            btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
    });

    /* ---- Fix checklist -> live projected score + ring ---- */
    var projectedEl = document.getElementById('projected-score');
    var deltaEl = document.getElementById('projected-delta');
    var ring = document.querySelector('.progress-circle');
    var checks = document.querySelectorAll('.fix-check');
    if (projectedEl && checks.length) {
        var current = parseFloat(projectedEl.dataset.current) || 0;
        var CIRC = 565.49;
        function recompute() {
            var gained = 0;
            checks.forEach(function (cb) {
                if (cb.checked) gained += parseFloat(cb.dataset.points) || 0;
            });
            var projected = Math.min(100, current + gained);
            projectedEl.textContent = projected.toFixed(1);
            if (deltaEl) {
                deltaEl.textContent = gained > 0
                    ? '+' + gained.toFixed(1) + ' pts from ticked fixes'
                    : 'Tick a fix to see your projected score move';
            }
            if (ring) {
                ring.style.strokeDashoffset = String(CIRC * (1 - projected / 100));
            }
        }
        checks.forEach(function (cb) { cb.addEventListener('change', recompute); });
    }

    /* ---- Per-bullet rewrites (login-gated server-side) ---- */
    document.querySelectorAll('.rewrite-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var out = btn.parentElement.querySelector('.rewrite-out');
            if (!out) return;
            btn.disabled = true;
            out.innerHTML = '<p style="font-size:.85rem;">Rewriting…</p>';
            fetch('/rewrite-bullet', {
                method: 'POST', headers: csrfHeaders(),
                body: JSON.stringify({ bullet_text: btn.dataset.bullet || '' })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                btn.disabled = false;
                if (!data.success) {
                    out.innerHTML = '<p style="font-size:.85rem;color:var(--accent-danger);">'
                        + esc(data.error || 'Rewrite failed.') + '</p>';
                    return;
                }
                var html = '';
                (data.rewrites || []).forEach(function (v) {
                    html += '<div class="rewrite-variant"><strong>' + esc(v.label)
                        + '</strong><p>' + esc(v.text) + '</p>'
                        + (v.tip ? '<p style="font-size:.8rem;">' + esc(v.tip) + '</p>' : '')
                        + '</div>';
                });
                out.innerHTML = html || '<p style="font-size:.85rem;">No variants returned.</p>';
            })
            .catch(function () {
                btn.disabled = false;
                out.innerHTML = '<p style="font-size:.85rem;color:var(--accent-danger);">Network error. Please try again.</p>';
            });
        });
    });

    /* ---- Inline JD match (login-gated server-side) ---- */
    var jdBtn = document.getElementById('jd-run');
    var jdText = document.getElementById('jd-text');
    var jdOut = document.getElementById('jd-out');
    if (jdBtn && jdText && jdOut) {
        jdBtn.addEventListener('click', function () {
            var text = jdText.value.trim();
            if (!text) { jdOut.innerHTML = '<p style="color:var(--accent-danger);">Paste a job description first.</p>'; return; }
            jdBtn.disabled = true;
            jdOut.innerHTML = '<p>Matching…</p>';
            fetch('/jd-match', {
                method: 'POST', headers: csrfHeaders(),
                body: JSON.stringify({ jd_text: text, resume_source: 'latest' })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                jdBtn.disabled = false;
                if (!data.success || !data.report) {
                    jdOut.innerHTML = '<p style="color:var(--accent-danger);">'
                        + esc(data.error || 'JD match failed.') + '</p>';
                    return;
                }
                var rep = data.report;
                var html = '<div class="jd-result"><strong>JD match: '
                    + esc(rep.score != null ? rep.score : '?') + '%</strong>'
                    + (rep.job_title ? ' — ' + esc(rep.job_title) : '') + '</div>';
                if (Array.isArray(rep.missing_skills) && rep.missing_skills.length) {
                    html += '<p><strong>Missing skills:</strong> ' + esc(rep.missing_skills.join(', ')) + '</p>';
                }
                if (Array.isArray(rep.matched_skills) && rep.matched_skills.length) {
                    html += '<p><strong>Matched skills:</strong> ' + esc(rep.matched_skills.join(', ')) + '</p>';
                }
                if (Array.isArray(rep.suggestions) && rep.suggestions.length) {
                    html += '<ul>' + rep.suggestions.map(function (s) {
                        return '<li>' + esc(typeof s === 'string' ? s : (s.text || s.title || '')) + '</li>';
                    }).join('') + '</ul>';
                }
                if (data.saved_url) {
                    html += '<p><a href="' + esc(data.saved_url) + '">Open the full JD report →</a></p>';
                }
                jdOut.innerHTML = html;
            })
            .catch(function () {
                jdBtn.disabled = false;
                jdOut.innerHTML = '<p style="color:var(--accent-danger);">Network error. Please try again.</p>';
            });
        });
    }
})();
