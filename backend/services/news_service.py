"""
News / Announcements service for the UST Reception Dashboard.

For the prototype, this returns a curated set of realistic UST Global
internal announcements.  The data is static (no scraping), which avoids
any sanitisation or external-request concerns.

Future upgrade path: replace `ANNOUNCEMENTS` with a call to an internal
SharePoint / Confluence / Slack feed endpoint that returns JSON already
screened by your intranet's access controls.
"""

import time
import random
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Curated announcements – realistic UST Global internal content
# ---------------------------------------------------------------------------
ANNOUNCEMENTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "category": "🏢 Company",
        "title": "UST Ranked Among Fortune's Best Workplaces in Technology 2025",
        "summary": "UST has been recognised for the third consecutive year, reflecting our commitment to a people-first culture across all global offices.",
        "ts_offset": -3600 * 2,   # 2 h ago
        "priority": "high",
    },
    {
        "id": 2,
        "category": "🤝 Clients",
        "title": "Strategic Partnership Signed with a Leading US Healthcare Network",
        "summary": "UST's Digital Engineering team will co-develop next-generation patient engagement platforms for a Fortune 500 healthcare group.",
        "ts_offset": -3600 * 5,
        "priority": "high",
    },
    {
        "id": 3,
        "category": "🌱 Sustainability",
        "title": "Cyberjaya Campus Achieves LEED Gold Certification",
        "summary": "Our Malaysia campus has completed its green building audit, reducing energy consumption by 34 % year-on-year.",
        "ts_offset": -3600 * 8,
        "priority": "normal",
    },
    {
        "id": 4,
        "category": "🎓 Learning",
        "title": "Q2 AI & Machine Learning Academy Cohort Now Open",
        "summary": "Enrolment for the 12-week internal AI programme is open to all engineers. Apply via the UST Learning Portal by 30 March.",
        "ts_offset": -3600 * 10,
        "priority": "normal",
    },
    {
        "id": 5,
        "category": "🏆 Awards",
        "title": "UST Wins Delivery Excellence Award at Global IT Summit",
        "summary": "The Cloud Migration Centre of Excellence was recognised for cutting average migration time by 40 % using proprietary automation.",
        "ts_offset": -3600 * 24,
        "priority": "high",
    },
    {
        "id": 6,
        "category": "📣 Events",
        "title": "All-Hands Town Hall – Q1 Business Review: 14 March at 10:00 AM MYT",
        "summary": "Join the live stream on Teams. CEO Kumar Mahadeva will cover business highlights, attrition trends, and our 2025 growth strategy.",
        "ts_offset": -3600 * 28,
        "priority": "urgent",
    },
    {
        "id": 7,
        "category": "🚀 Innovation",
        "title": "GenAI Hackathon 2025 – Submissions Close 22 March",
        "summary": "Over 200 teams across 14 countries have registered. Final showcase will be streamed globally. Visit the hackathon portal to submit.",
        "ts_offset": -3600 * 36,
        "priority": "normal",
    },
    {
        "id": 8,
        "category": "🌍 Community",
        "title": "UST Cares: Blood Donation Drive – 18 March, Cyberjaya Lobby",
        "summary": "Partner hospital has confirmed 120 donation slots. Register through the internal portal. All donors receive complimentary lunch.",
        "ts_offset": -3600 * 48,
        "priority": "normal",
    },
]

class NewsService:
    def get_news(self) -> List[Dict[str, Any]]:
        """Return all announcements with live timestamps."""
        now = time.time()
        result = []
        for item in ANNOUNCEMENTS:
            result.append({
                "id":       item["id"],
                "category": item["category"],
                "title":    item["title"],
                "summary":  item["summary"],
                "priority": item["priority"],
                "timestamp": now + item["ts_offset"],
            })
        return result


# Module-level singleton
news_service = NewsService()
