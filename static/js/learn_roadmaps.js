/* Learn roadmaps page JS (Wave 3 #18): skill filter, gap analyzer, progress toggles. */
(function () {
    'use strict';

    var tokenMeta = document.querySelector('meta[name="csrf-token"]');
    function headers() {
        var h = { 'Content-Type': 'application/json' };
        if (tokenMeta) h['X-CSRFToken'] = tokenMeta.getAttribute('content');
        return h;
    }
    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /* ---- skill domain filter + name search (roadmaps home) ---- */
    var filter = document.getElementById('skill-filter');
    var skillSearch = document.getElementById('skill-search');
    function applySkillFilters() {
        var want = filter ? filter.value : '';
        var q = skillSearch ? skillSearch.value.trim().toLowerCase() : '';
        document.querySelectorAll('.skill-card').forEach(function (card) {
            var name = (card.querySelector('h3') || {}).textContent || '';
            var okDomain = !want || card.dataset.domain === want;
            var okName = !q || name.toLowerCase().indexOf(q) !== -1;
            card.style.display = (okDomain && okName) ? '' : 'none';
        });
    }
    if (filter) filter.addEventListener('change', applySkillFilters);
    if (skillSearch) skillSearch.addEventListener('input', applySkillFilters);

    /* ---- hero Ripple Dissolve: same water-ripple filter as the Learn
       hero, applied to the centred heading block on first view ---- */
    (function () {
        var text = document.getElementById('roadmap-hero-text');
        var disp = document.getElementById('rm-ripple-disp');
        if (!text || !disp) return;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        text.classList.add('sb-rippling');
        text.style.opacity = '0';
        text.style.filter = 'url(#rm-ripple-dissolve) blur(10px)';
        var done = false;
        function finish() {
            if (done) return;
            done = true;
            disp.setAttribute('scale', '0');
            text.classList.remove('sb-rippling');
            text.style.opacity = '';
            text.style.filter = '';
        }
        var io = new IntersectionObserver(function (entries) {
            if (!entries[0].isIntersecting) return;
            io.disconnect();
            var DUR = 2800, t0 = null;
            function frame(now) {
                if (done) return;
                if (t0 === null) t0 = now;
                var p = Math.min(1, (now - t0) / DUR);
                var e = 1 - Math.pow(1 - p, 3);
                disp.setAttribute('scale', String(Math.round(140 * (1 - e))));
                text.style.opacity = String(e.toFixed(3));
                text.style.filter = 'url(#rm-ripple-dissolve) blur(' + (10 * (1 - e)).toFixed(1) + 'px)';
                if (p < 1) { requestAnimationFrame(frame); } else { finish(); }
            }
            requestAnimationFrame(frame);
            setTimeout(finish, DUR + 1200);
        }, { threshold: 0.2 });
        io.observe(text);
    })();

    /* ---- gap form helpers: role preview, skill search, counters ---- */
    var roleSel = document.getElementById('gap-role');
    var roleDesc = document.getElementById('gap-role-desc');
    if (roleSel && roleDesc) {
        roleSel.addEventListener('change', function () {
            var opt = roleSel.options[roleSel.selectedIndex];
            roleDesc.textContent = (opt && opt.dataset.desc) || '';
            document.getElementById('gap-step-1').classList.toggle('is-done', !!roleSel.value);
        });
    }
    function updateGapCounts() {
        var boxes = document.querySelectorAll('.gap-skill');
        var checked = document.querySelectorAll('.gap-skill:checked');
        var countEl = document.getElementById('gap-selected-count');
        if (countEl) countEl.textContent = checked.length + (checked.length === 1 ? ' skill selected' : ' skills selected');
        document.querySelectorAll('.gap-domain').forEach(function (details) {
            var badge = details.querySelector('.gap-domain-count');
            if (!badge) return;
            var n = details.querySelectorAll('.gap-skill:checked').length;
            badge.textContent = n ? '(' + n + ' selected)' : '';
        });
        var step2 = document.getElementById('gap-step-2');
        if (step2) step2.classList.toggle('is-done', checked.length > 0);
    }
    document.querySelectorAll('.gap-skill').forEach(function (cb) {
        cb.addEventListener('change', updateGapCounts);
    });
    var gapSearch = document.getElementById('gap-skill-search');
    if (gapSearch) {
        gapSearch.addEventListener('input', function () {
            var q = gapSearch.value.trim().toLowerCase();
            document.querySelectorAll('.gap-domain').forEach(function (details) {
                var anyVisible = false;
                details.querySelectorAll('.gap-skill-card').forEach(function (label) {
                    var name = (label.textContent || '').toLowerCase();
                    var show = !q || name.indexOf(q) !== -1;
                    label.style.display = show ? '' : 'none';
                    if (show) anyVisible = true;
                });
                if (q) details.open = anyVisible;
                details.style.display = (!q || anyVisible) ? '' : 'none';
            });
        });
    }
    var expandBtn = document.getElementById('gap-expand-all');
    if (expandBtn) {
        expandBtn.addEventListener('click', function () {
            var allOpen = Array.from(document.querySelectorAll('.gap-domain')).every(function (d) { return d.open; });
            document.querySelectorAll('.gap-domain').forEach(function (d) { d.open = !allOpen; });
            expandBtn.textContent = allOpen ? 'Expand all' : 'Collapse all';
        });
    }
    var clearBtn = document.getElementById('gap-clear');
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            document.querySelectorAll('.gap-skill:checked').forEach(function (cb) { cb.checked = false; });
            updateGapCounts();
        });
    }
    updateGapCounts();

    /* ---- gap analyzer ---- */
    var runBtn = document.getElementById('gap-run');
    if (runBtn) {
        runBtn.addEventListener('click', function () {
            var role = document.getElementById('gap-role').value;
            var status = document.getElementById('gap-status');
            var result = document.getElementById('gap-result');
            if (!role) {
                status.textContent = 'Please choose a target role first.';
                return;
            }
            var current = [];
            document.querySelectorAll('.gap-skill:checked').forEach(function (cb) {
                var stageSel = cb.closest('label').querySelector('.gap-stage');
                current.push({ skill_id: cb.value, stage: stageSel ? stageSel.value : 'beginner' });
            });
            status.textContent = 'Analyzing gaps…';
            result.innerHTML = '';
            fetch('/learn/roadmaps/gap', {
                method: 'POST', headers: headers(),
                body: JSON.stringify({ target_role: role, current_skills: current })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success) {
                    status.textContent = data.error || 'Analysis failed.';
                    return;
                }
                status.textContent = '';
                renderGap(result, data);
            })
            .catch(function () { status.textContent = 'Network error. Please try again.'; });
        });
    }

    function renderGap(root, data) {
        var html = '';
        html += '<div class="b-card b-card--lite" style="margin-bottom:1rem;"><div class="b-kv">'
            + '<div class="b-kv-row"><span class="b-kv-label">Target role</span><span class="b-kv-val">' + esc(data.role.name) + '</span></div>'
            + '<div class="b-kv-row"><span class="b-kv-label">Skills to close</span><span class="b-kv-val">' + data.num_skills + '</span></div>'
            + '<div class="b-kv-row"><span class="b-kv-label">Estimated effort</span><span class="b-kv-val">' + data.total_weeks + ' weeks</span></div>'
            + '</div>'
            + '<div class="b-flash b-flash--info" style="margin:1rem 0 0;"><strong>Study tip' + (data.ai_powered ? ' (AI)' : '') + ':</strong> ' + esc(data.study_tip) + '</div></div>';
        if (!data.gaps.length) {
            html += '<div class="b-flash b-flash--success"><strong>No gaps found</strong> — you already meet every required skill for this role. Consider a harder target role.</div>';
        } else {
            html += '<div class="b-bento">';
            var weekCursor = 0;
            data.gaps.forEach(function (g, i) {
                var wStart = weekCursor + 1;
                weekCursor += (g.weeks_needed || 0);
                var pct = Math.round((g.priority / 5) * 100);
                html += '<div class="b-card b-card--lite gap-result-card" style="animation-delay:' + (i * 0.06) + 's;">'
                    + '<div style="display:flex;justify-content:space-between;gap:.6rem;align-items:baseline;">'
                    + '<h3 style="margin:0;">' + (i + 1) + '. ' + esc(g.skill_name) + '</h3>'
                    + '<span class="b-tag">priority ' + g.priority + '/5</span></div>'
                    + '<div class="gap-prio-bar" aria-hidden="true"><span style="width:' + pct + '%;"></span></div>'
                    + '<p style="color:var(--b-muted);font-size:.9rem;">' + esc(g.reason) + '</p>'
                    + '<div class="b-kv">'
                    + '<div class="b-kv-row"><span class="b-kv-label">You are at</span><span class="b-kv-val">' + esc(g.current_stage || 'not started') + '</span></div>'
                    + '<div class="b-kv-row"><span class="b-kv-label">Need</span><span class="b-kv-val">' + esc(g.min_stage) + '</span></div>'
                    + '<div class="b-kv-row"><span class="b-kv-label">Plan slot</span><span class="b-kv-val">weeks ' + wStart + '–' + weekCursor + ' (' + g.weeks_needed + ' weeks)</span></div>'
                    + '</div>'
                    + '<a class="b-btn b-btn--ghost b-btn--sm" style="margin-top:.8rem;" href="/learn/roadmaps/' + encodeURIComponent(g.skill_id) + '">Open roadmap</a>'
                    + '</div>';
            });
            html += '</div>';
        }
        root.innerHTML = html;
        var step3 = document.getElementById('gap-step-3');
        if (step3) step3.classList.add('is-done');
        root.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    /* ---- stage progress toggles (roadmap detail) ---- */
    document.querySelectorAll('.stage-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var payload = {
                skill_id: btn.dataset.skill,
                stage: btn.dataset.stage,
                status: btn.dataset.status
            };
            fetch('/learn/roadmaps/progress', {
                method: 'POST', headers: headers(), body: JSON.stringify(payload)
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success) return;
                // refresh the button group to reflect the new state
                var group = btn.parentElement;
                group.querySelectorAll('.stage-btn').forEach(function (b) {
                    var active = b.dataset.status === data.status;
                    b.classList.toggle('b-btn--primary', active);
                    b.classList.toggle('b-btn--ghost', !active);
                });
            })
            .catch(function () { /* silent: non-critical */ });
        });
    });
})();
