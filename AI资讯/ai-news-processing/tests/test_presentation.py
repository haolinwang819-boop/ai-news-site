import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.presentation import _enrichment_quality_issues  # noqa: E402


class PresentationQualityTests(unittest.TestCase):
    def test_quality_gate_rejects_non_english_and_repeated_bullets(self) -> None:
        chunk = [
            {
                "url": "https://example.com/story",
                "title": "Original source title",
            }
        ]
        enrichment = {
            "https://example.com/story": {
                "display_title": "OpenAI expands enterprise Codex access",
                "summary": "天立启鸣AI研究院院长刘志毅，入选2025福布斯中国科创人物。",
                "key_points": [
                    "Codex is rolling out to large enterprises this quarter.",
                    "Codex is rolling out to large enterprises this quarter.",
                    "The rollout includes new workflow controls for engineering teams.",
                ],
            }
        }

        issues = _enrichment_quality_issues(chunk, enrichment)
        self.assertTrue(any("summary is not English" in issue for issue in issues))

    def test_quality_gate_requires_exactly_one_sentence_summary(self) -> None:
        chunk = [
            {
                "url": "https://example.com/story",
                "title": "Original source title",
            }
        ]
        enrichment = {
            "https://example.com/story": {
                "display_title": "Anthropic adds new workspace controls for Claude",
                "summary": "Anthropic added new workspace controls. The update also expands audit visibility.",
                "key_points": [
                    "Admins can now manage permissions from a central workspace panel.",
                    "The release expands audit visibility for sensitive team actions.",
                    "Anthropic positioned the change as an enterprise governance upgrade.",
                ],
            }
        }

        issues = _enrichment_quality_issues(chunk, enrichment)
        self.assertTrue(any("summary is not exactly one sentence" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
