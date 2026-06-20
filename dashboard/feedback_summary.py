from __future__ import annotations

from collections import Counter
from typing import Any


def summarize_feedback(records: list[dict[str, Any]]) -> dict[str, Any]:
    issue_counts = Counter(record.get("issue_category", "unknown") for record in records)
    status_counts = Counter(record.get("review_status", "unknown") for record in records)
    type_counts = Counter(record.get("feedback_type", "unknown") for record in records)
    return {
        "total_count": len(records),
        "negative_count": sum(record.get("user_rating") == "negative" for record in records),
        "unresolved_count": sum(record.get("review_status") in {"open", "triaged"} for record in records),
        "by_issue_category": dict(sorted(issue_counts.items())),
        "by_review_status": dict(sorted(status_counts.items())),
        "by_feedback_type": dict(sorted(type_counts.items())),
        "top_issue_categories": [
            {"issue_category": issue, "count": count}
            for issue, count in issue_counts.most_common(5)
        ],
    }

