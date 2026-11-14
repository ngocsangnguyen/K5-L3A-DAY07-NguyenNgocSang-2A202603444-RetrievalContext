import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))
from evaluate_retrievers import evaluate


class FilterCaptureRetriever:
    def __init__(self):
        self.filters = None

    def search(self, query, *, filters=None, top_k=3):
        self.filters = filters
        return []


class EvaluateRetrieverTests(unittest.TestCase):
    def test_passes_singular_benchmark_filter_to_retriever(self):
        retriever = FilterCaptureRetriever()
        question = {
            "id": "q",
            "split": "dev",
            "question": "example",
            "gold_source_id": "doc",
            "gold_page": 1,
            "evidence_quote": "evidence",
            "filter": {"chapter": "chapter_2"},
        }

        traces = evaluate(retriever, [question], "test")

        self.assertEqual(retriever.filters, {"chapter": "chapter_2"})
        self.assertEqual(traces[0]["filters"], {"chapter": "chapter_2"})


if __name__ == "__main__":
    unittest.main()
