"""AI-era quiz expansion (2026-10-24): 6 new skills x 30 questions.

Guards the merged bank: 660 questions / 22 skills, every new skill at
30, unique ids, and every row answerable (4 options, valid index).
"""

from collections import Counter

from studybuddy.skill_quizzes import _load as load_quiz_bank

NEW_SKILLS = ["nlp", "generative-ai", "agentic-ai",
              "computer-vision", "mlops", "reinforcement-learning"]


def test_quiz_bank_counts():
    bank = load_quiz_bank()
    counts = Counter(q["skill"] for q in bank)
    assert len(bank) == 660
    assert len(counts) == 22
    for skill in NEW_SKILLS:
        assert counts[skill] == 30


def test_quiz_ids_unique_and_rows_answerable():
    bank = load_quiz_bank()
    ids = [q["id"] for q in bank]
    assert len(ids) == len(set(ids))
    for q in bank:
        assert len(q["options"]) == 4
        assert 0 <= q["answer"] <= 3
        assert q["difficulty"] in ("easy", "medium", "hard")
        assert q["explanation"]
