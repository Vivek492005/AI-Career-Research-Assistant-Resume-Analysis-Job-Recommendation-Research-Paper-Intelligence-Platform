"""Regression: multi-worker SQLite boot race in create_all.

Two gunicorn workers booting against a fresh SQLite file both pass
create_all's checkfirst probe and both issue CREATE TABLE; the loser
died with "table llm_usage already exists" and gunicorn's master shut
down ("Worker failed to boot") — this is what kept the Lighthouse CI
job red. ``_create_all_race_safe`` must tolerate exactly that race and
let every other database error propagate.
"""
import pytest
from sqlalchemy.exc import OperationalError

import unified_app


def _already_exists_error():
    return OperationalError(
        "CREATE TABLE llm_usage (...)", None,
        Exception("table llm_usage already exists"),
    )


def test_race_safe_create_all_tolerates_already_exists(monkeypatch):
    calls = {"n": 0}

    def flaky_create_all():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _already_exists_error()

    monkeypatch.setattr(unified_app.db, "create_all", flaky_create_all)
    monkeypatch.setattr(unified_app.db.session, "remove", lambda: None)
    unified_app._create_all_race_safe()
    assert calls["n"] == 3


def test_race_safe_create_all_propagates_other_errors(monkeypatch):
    def broken_create_all():
        raise OperationalError(
            "CREATE TABLE x (...)", None,
            Exception("database is locked"),
        )

    monkeypatch.setattr(unified_app.db, "create_all", broken_create_all)
    with pytest.raises(OperationalError):
        unified_app._create_all_race_safe()
