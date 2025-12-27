import pytest
import datetime
import math
from modules.dashboard_widgets import calculate_brain_battery

# --- 1. THE TIME MACHINE (MOCKING) ---
@pytest.fixture
def mock_today(monkeypatch):
    class MockDate(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(2025, 1, 10)
    monkeypatch.setattr(datetime, 'date', MockDate)

# --- 2. THE TEST CASES ---

def test_new_user(mock_today):
    """Scenario 1: No history -> 0%."""
    data = {"revision_history": []}
    assert calculate_brain_battery(data) == 0

def test_fresh_revision(mock_today):
    """Scenario 2: Studied today -> 100%."""
    data = {"revision_history": [{"date": "2025-01-10"}]}
    assert calculate_brain_battery(data) == 100

def test_decay_one_revision(mock_today):
    """
    Scenario 3: Studied ONCE, 1 day ago.
    Stability (S) = 1.0
    Time (t) = 1 day
    Math: exp(-1/1) = 0.367 -> ~37%
    Old Linear Logic would have been 90%. New Logic is harsh!
    """
    data = {"revision_history": [{"date": "2025-01-09"}]}
    score = calculate_brain_battery(data)
    # Allow small rounding difference (+/- 1)
    assert 36 <= score <= 38 

def test_decay_multiple_revisions(mock_today):
    """
    Scenario 4: Studied 3 times. Last time was 5 days ago.
    Stability (S) for 3 revisions = 7.0 days.
    Time (t) = 5 days.
    Math: exp(-5/7) = exp(-0.714) = ~0.489 -> ~49%
    """
    data = {
        "revision_history": [
            {"date": "2025-01-01"},
            {"date": "2025-01-03"},
            {"date": "2025-01-05"} # Last revision (5 days ago relative to Jan 10)
        ]
    }
    score = calculate_brain_battery(data)
    assert 48 <= score <= 50

def test_long_term_mastery(mock_today):
    """
    Scenario 5: Studied 5 times (Mastery). Last time 2 weeks ago.
    Stability (S) = 7 * 2^(5-3) = 7 * 4 = 28 days.
    Time (t) = 14 days.
    Math: exp(-14/28) = exp(-0.5) = 0.606 -> ~61%
    (User still remembers 61% even after 2 weeks because they studied 5 times!)
    """
    data = {
        "revision_history": [
            {"date": "2024-12-01"}, {"date": "2024-12-05"},
            {"date": "2024-12-10"}, {"date": "2024-12-15"},
            {"date": "2024-12-27"} # 14 days ago relative to Jan 10
        ]
    }
    score = calculate_brain_battery(data)
    assert 60 <= score <= 62