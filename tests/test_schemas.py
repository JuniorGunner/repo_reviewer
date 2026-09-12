from app.schemas import Finding, ReviewReport


def test_review_report_defaults():
    report = ReviewReport(score=80, summary="Good")
    assert report.confirmed_findings == []


def test_finding_accepts_high_severity():
    finding = Finding(
        severity="high",
        category="reliability",
        file="app.py",
        issue="Missing timeout",
        evidence="requests.get(...)",
        recommendation="Set a timeout.",
    )
    assert finding.severity == "high"
