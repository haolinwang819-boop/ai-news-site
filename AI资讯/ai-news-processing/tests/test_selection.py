import copy
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import SCREENING_CONFIG  # noqa: E402
from scripts.selection import deterministic_prefilter, merge_shortlist_candidates  # noqa: E402


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config = copy.deepcopy(SCREENING_CONFIG)
        SCREENING_CONFIG["per_source_cap"] = 2
        SCREENING_CONFIG["max_items"] = 5
        SCREENING_CONFIG["shortlist_targets"] = {
            "breakout_products": 2,
            "hot_news": 1,
            "llm": 1,
            "image_video": 1,
            "product_updates": 0,
        }

    def tearDown(self) -> None:
        SCREENING_CONFIG.clear()
        SCREENING_CONFIG.update(self._original_config)

    def test_deterministic_prefilter_removes_duplicates_and_caps_sources(self) -> None:
        items = [
            {
                "url": "https://example.com/a",
                "title": "Claude launches coding workflow",
                "source": "Example",
                "content": "Claude launches a coding workflow with MCP integration and local agent support.",
            },
            {
                "url": "https://example.com/b",
                "title": "Claude launches coding workflow!",
                "source": "Example",
                "content": "Near duplicate title that should be removed before AI review.",
            },
            {
                "url": "https://example.com/c",
                "title": "OpenAI ships new enterprise feature",
                "source": "Example",
                "content": "This third item survives because the near-duplicate title above was already removed.",
            },
            {
                "url": "https://example.com/d",
                "title": "Gemini adds a browser assistant",
                "source": "Other",
                "content": "Gemini adds a browser assistant that can help people summarize web pages.",
            },
        ]

        filtered = deterministic_prefilter(items)
        self.assertEqual(
            [item["url"] for item in filtered],
            ["https://example.com/a", "https://example.com/c", "https://example.com/d"],
        )

    def test_merge_shortlist_candidates_respects_targets_then_backfills(self) -> None:
        kept = [
            {"url": "https://a1", "title": "A1", "category": "breakout_products", "selection_score": 95, "published_time": "2026-04-20T10:00:00+00:00"},
            {"url": "https://a2", "title": "A2", "category": "breakout_products", "selection_score": 90, "published_time": "2026-04-20T09:00:00+00:00"},
            {"url": "https://a3", "title": "A3", "category": "breakout_products", "selection_score": 88, "published_time": "2026-04-20T08:00:00+00:00"},
            {"url": "https://h1", "title": "H1", "category": "hot_news", "selection_score": 85, "published_time": "2026-04-20T07:00:00+00:00"},
            {"url": "https://l1", "title": "L1", "category": "llm", "selection_score": 80, "published_time": "2026-04-20T06:00:00+00:00"},
            {"url": "https://i1", "title": "I1", "category": "image_video", "selection_score": 75, "published_time": "2026-04-20T05:00:00+00:00"},
            {"url": "https://h2", "title": "H2", "category": "hot_news", "selection_score": 70, "published_time": "2026-04-20T04:00:00+00:00"},
        ]

        shortlist = merge_shortlist_candidates(kept)
        self.assertEqual([item["url"] for item in shortlist], ["https://a1", "https://a2", "https://h1", "https://l1", "https://i1"])


if __name__ == "__main__":
    unittest.main()
