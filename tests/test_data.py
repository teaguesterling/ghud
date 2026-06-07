# tests/test_data.py
from datetime import datetime, timedelta, timezone

from ghud.data import (
    collect_other_activity,
    filter_important_notifications,
    filter_recent_issues,
    IMPORTANT_REASONS,
)


def _iso(days_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_filter_recent_issues_drops_old_backlog():
    issues = [
        {"title": "fresh", "createdAt": _iso(2)},
        {"title": "stale", "createdAt": _iso(400)},
    ]
    recent = filter_recent_issues(issues, days=7)
    assert [i["title"] for i in recent] == ["fresh"]


def test_filter_recent_issues_disabled_with_nonpositive_days():
    issues = [{"title": "stale", "createdAt": _iso(400)}]
    assert filter_recent_issues(issues, days=0) == issues


def test_filter_recent_issues_keeps_unparseable_dates():
    issues = [{"title": "weird", "createdAt": ""}]
    assert filter_recent_issues(issues, days=7) == issues


def test_collect_other_activity_splits_by_portfolio():
    notifications = [
        {"repository": {"full_name": "org/tracked"}, "reason": "mention"},
        {"repository": {"full_name": "org/other"}, "reason": "subscribed"},
        {"repository": {"full_name": "org/other"}, "reason": "mention"},
    ]
    portfolio, other = collect_other_activity(notifications, {"org/tracked"})
    assert len(portfolio) == 1
    assert portfolio[0]["repository"]["full_name"] == "org/tracked"
    assert len(other) == 1
    assert other[0]["repo"] == "org/other"
    assert other[0]["count"] == 2


def test_filter_important_notifications():
    notifications = [
        {"reason": "review_requested", "subject": {"title": "A"}},
        {"reason": "subscribed", "subject": {"title": "B"}},
        {"reason": "mention", "subject": {"title": "C"}},
    ]
    important = filter_important_notifications(notifications)
    assert len(important) == 2
    titles = {n["subject"]["title"] for n in important}
    assert titles == {"A", "C"}


def test_filter_important_notifications_returns_all_when_flag_false():
    notifications = [
        {"reason": "subscribed", "subject": {"title": "B"}},
    ]
    result = filter_important_notifications(notifications, important_only=False)
    assert len(result) == 1


def test_important_reasons_contains_expected():
    assert "review_requested" in IMPORTANT_REASONS
    assert "security_alert" in IMPORTANT_REASONS
    assert "subscribed" not in IMPORTANT_REASONS
