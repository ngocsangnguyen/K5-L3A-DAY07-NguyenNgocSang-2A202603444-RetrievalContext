
import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from agentic import run_agent
from dense_retriever import DenseRetriever
from tfidf_retriever import TfidfRetriever
from hybrid_retriever import HybridRetriever
from llm_controller import LLMController


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument(
        "--retriever",
        choices=["tfidf", "dense", "hybrid"],
        default="hybrid"
    )
    parser.add_argument("--max-searches", type=int, default=4)
    parser.add_argument("--budget", type=int, default=800)
    args = parser.parse_args()

    day6_root = Path(os.environ["DAY6_ROOT"])

    load_dotenv(day6_root / ".env", override=True)
    load_dotenv(ROOT / ".env", override=True)

    cases_path = ROOT / "benchmark" / "agent_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    selected = [c for c in cases if c["split"] == args.split]

    retriever_classes = {
        "tfidf": TfidfRetriever,
        "dense": DenseRetriever,
        "hybrid": HybridRetriever,
    }

    controller = LLMController()
    retriever = retriever_classes[args.retriever](strategy="A")

    traces = []

    for i, case in enumerate(selected, 1):
        print(f"\n[{i}/{len(selected)}] {case['id']}: {case['question']}", flush=True)

        start = time.perf_counter()

        try:
            result = run_agent(
                case["question"],
                controller,
                retriever,
                max_searches=args.max_searches,
                top_k=3,
                budget=args.budget,
            )
        except Exception as exc:
            result = {
                "status": "error",
                "answer": "",
                "citations": [],
                "events": [],
                "error": f"{type(exc).__name__}: {exc}",
            }

        elapsed = time.perf_counter() - start
        events = result.get("events", [])
        searches = sum(e.get("event") == "search" for e in events)

        trace = {
            "query_id": case["id"],
            "split": args.split,
            "question": case["question"],
            "retriever": args.retriever,
            "model": controller.model,
            "max_searches": args.max_searches,
            "top_k": 3,
            "budget_chars": args.budget,
            "search_calls": searches,
            "elapsed_seconds": elapsed,
            **result,
        }

        traces.append(trace)

        print(
            f"Status={trace['status']} | "
            f"Searches={searches} | "
            f"Time={elapsed:.2f}s",
            flush=True
        )

        # Lưu sau từng case để không mất dữ liệu khi chạy lỗi
        output_dir = ROOT / "report" / "agent"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / (
            f"{args.retriever}_{args.split}_traces.json"
        )

        output_file.write_text(
            json.dumps(traces, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    print("\n========== SUMMARY ==========")
    print("Total:", len(traces))
    print("Answered:", sum(t["status"] == "answered" for t in traces))
    print("Abstained:", sum(t["status"] == "abstain" for t in traces))
    print("Errors:", sum(t["status"] == "error" for t in traces))
    print("Saved:", output_file)


if __name__ == "__main__":
    main()
