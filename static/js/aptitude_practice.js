/* Aptitude topic practice: one question at a time, instant feedback. */
(function () {
    "use strict";

    var root = document.getElementById("practice-root");
    if (!root) return;
    var questions = [];
    try {
        questions = JSON.parse(
            document.getElementById("practice-data").textContent) || [];
    } catch (e) { questions = []; }

    var CSRF = (document.querySelector('meta[name="csrf-token"]') || {})
        .content || "";
    var idx = 0, chosen = null, checked = false, score = 0, attempted = 0;
    var box = document.getElementById("pr-question");
    var feedback = document.getElementById("pr-feedback");
    var errBox = document.getElementById("pr-error");
    var checkBtn = document.getElementById("pr-check");
    var nextBtn = document.getElementById("pr-next");
    var progress = document.getElementById("pr-progress");
    var scoreEl = document.getElementById("pr-score");

    function el(tag, cls, text) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text !== undefined && text !== null) n.textContent = text;
        return n;
    }

    function render() {
        chosen = null;
        checked = false;
        feedback.innerHTML = "";
        errBox.textContent = "";
        checkBtn.style.display = "";
        nextBtn.style.display = "none";
        box.innerHTML = "";
        if (!questions.length) {
            box.appendChild(el("p", null, "No questions for this topic yet."));
            checkBtn.style.display = "none";
            return;
        }
        var q = questions[idx];
        progress.textContent = "Question " + (idx + 1) + " of " +
            questions.length;
        scoreEl.textContent = "Score: " + score + "/" + attempted;
        var card = el("div", "ap-q");
        var meta = el("div", "ap-qmeta");
        meta.appendChild(el("span", "ap-chip", q.category));
        meta.appendChild(el("span", "ap-chip", q.subcategory.replace(/_/g, " ")));
        meta.appendChild(el("span", "ap-chip diff-" + q.difficulty, q.difficulty));
        (q.companies || []).forEach(function (c) {
            meta.appendChild(el("span", "ap-chip co", c + " pattern"));
        });
        card.appendChild(meta);
        card.appendChild(el("div", "ap-qtext", q.statement));
        q.options.forEach(function (opt, oi) {
            var lab = el("label", "ap-opt");
            var radio = document.createElement("input");
            radio.type = "radio";
            radio.name = "pr_q";
            radio.value = oi;
            radio.addEventListener("change", function () {
                chosen = oi;
                card.querySelectorAll(".ap-opt").forEach(function (o) {
                    o.classList.remove("sel");
                });
                lab.classList.add("sel");
            });
            lab.appendChild(radio);
            lab.appendChild(el("span", null, opt));
            card.appendChild(lab);
        });
        box.appendChild(card);
    }

    checkBtn.addEventListener("click", function () {
        if (checked) return;
        if (chosen === null) {
            errBox.textContent = "Pick an option first.";
            return;
        }
        var q = questions[idx];
        checkBtn.disabled = true;
        fetch("/aptitude/practice/check", {
            method: "POST",
            headers: { "Content-Type": "application/json",
                       "X-CSRFToken": CSRF },
            body: JSON.stringify({ question_id: q.id, chosen: chosen })
        }).then(function (r) {
            return r.json().then(function (d) {
                return { status: r.status, body: d };
            });
        }).then(function (res) {
            checkBtn.disabled = false;
            if (res.status !== 200 || !res.body.success) {
                errBox.textContent = (res.body && res.body.error) ||
                    "Check failed. Try again.";
                return;
            }
            checked = true;
            attempted += 1;
            var r = res.body.result;
            if (r.correct) score += 1;
            scoreEl.textContent = "Score: " + score + "/" + attempted;
            box.querySelectorAll(".ap-opt").forEach(function (lab, oi) {
                lab.classList.add("locked");
                if (oi === r.correct_index) lab.classList.add("correct");
                else if (oi === chosen) lab.classList.add("wrong");
            });
            var verdict = el("div", "ap-verdict " + (r.correct ? "ok" : "bad"),
                             r.correct ? "✓ Correct!" : "✗ Not quite.");
            feedback.appendChild(verdict);
            var expl = el("div", "ap-expl");
            expl.appendChild(el("strong", null, "Why: "));
            expl.appendChild(el("span", null, r.explanation));
            feedback.appendChild(expl);
            if (r.trick) {
                var trick = el("div", "ap-expl");
                trick.appendChild(el("strong", null, "Shortcut: "));
                trick.appendChild(el("span", null, r.trick));
                feedback.appendChild(trick);
            }
            checkBtn.style.display = "none";
            nextBtn.style.display = "";
            nextBtn.textContent = idx + 1 < questions.length
                ? "Next Question" : "Restart Practice";
        }).catch(function () {
            checkBtn.disabled = false;
            errBox.textContent = "Network error. Please try again.";
        });
    });

    nextBtn.addEventListener("click", function () {
        idx = (idx + 1) % questions.length;
        render();
    });

    render();
})();
