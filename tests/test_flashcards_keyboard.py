"""#12: flashcard keyboard navigation — ArrowLeft/ArrowRight move
between cards, Space/Enter flips, visible focus style on the card,
and an on-page keyboard hint. Full flow must work with no mouse.
"""
import os

from tests.conftest import login, register

REPO = os.path.join(os.path.dirname(__file__), "..")

TEXTS = [
    "Gradient descent is an optimization algorithm used to minimize loss functions. ",
    "Backpropagation is the algorithm used to compute gradients in neural networks. ",
    "Overfitting occurs when a model memorizes training data and fails to generalize. ",
    "Regularization is a technique that reduces overfitting by penalizing complexity. ",
    "Cross validation is a method for estimating model performance on unseen data.",
]


def _seed_deck(client, app):
    from unified_app import StudyDoc, User, db
    register(client)
    login(client)
    with app.app_context():
        user = User.query.filter_by(email="aarav@example.com").first()
        chunks = [{"page": i + 1, "index": i, "text": t, "heading": None}
                  for i, t in enumerate(TEXTS)]
        doc = StudyDoc(user_id=user.id, title="ML Notes",
                       num_pages=len(TEXTS), num_chunks=len(chunks),
                       char_count=sum(len(t) for t in TEXTS),
                       data={"chunks": chunks})
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
    r = client.post("/research/api/flashcards/generate",
                    json={"doc_id": doc_id})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["id"]


def test_flashcards_js_handles_arrow_keys():
    js = open(os.path.join(REPO, "static", "js", "flashcards.js"),
              encoding="utf-8").read()
    assert "ArrowRight" in js
    assert "ArrowLeft" in js
    # navigation must not hijack keys while the user is typing
    assert "TEXTAREA" in js and "INPUT" in js


def test_review_page_ships_keyboard_support(client, app):
    sid = _seed_deck(client, app)
    html = client.get("/research/flashcards/%d" % sid).get_data(as_text=True)
    # focus style for the flippable card + discoverable hint
    assert "#fc-card:focus-visible" in html
    assert 'id="fc-kbd-hint"' in html
    assert "Keyboard:" in html
    # the card stays a focusable, labelled button-role element
    assert 'id="fc-card"' in html and 'tabindex="0"' in html
    assert 'aria-label="Flip card"' in html
