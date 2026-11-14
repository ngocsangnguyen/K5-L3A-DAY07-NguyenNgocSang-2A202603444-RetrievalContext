
import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

load_dotenv(ROOT / ".env", override=False)

if not os.getenv("DAY6_ROOT"):
    os.environ["DAY6_ROOT"] = str(
        ROOT.parent /
        "K5-L3A-DAY06-NguyenNgocSang-2A202603444-DataIngestion"
    )

from baseline import pack_context
from tfidf_retriever import TfidfRetriever
from dense_retriever import DenseRetriever
from hybrid_retriever import HybridRetriever


def is_hit(chunk, question):
    """Kiểm tra chunk có chứa gold evidence hay không."""
    source = question.get("gold_source_id")
    page = question.get("gold_page")
    evidence = question.get("evidence_quote", "")

    if not source or page is None or not evidence:
        return False

    return (
        chunk.get("source_id") == source
        and str(chunk.get("page")) == str(page)
        and " ".join(evidence.split())
        in " ".join(chunk.get("text", "").split())
    )


def evaluate(retriever, questions, strategy, budget=800):
    traces = []

    for q in questions:
        start = time.perf_counter()

        filters = q.get("filters") or q.get("filter") or q.get("metadata_filter")
        if not isinstance(filters, dict):
            filters = None

        results = retriever.search(
            q["question"],
            filters=filters,
            top_k=3
        )

        context, context_ids = pack_context(
            results,
            budget=budget
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        marked = [
            {**chunk, "hit": is_hit(chunk, q)}
            for chunk in results
        ]

        hit1 = bool(marked and marked[0]["hit"])
        hit3 = any(chunk["hit"] for chunk in marked)
        context_hit = any(
            chunk["hit"] and chunk["id"] in context_ids
            for chunk in marked
        )

        traces.append({
            "query_id": q["id"],
            "question": q["question"],
            "split": q["split"],
            "strategy": strategy,
            "filters": filters,
            "results": marked,
            "context_ids": context_ids,
            "context_chars": len(context),
            "hit1": hit1,
            "hit3": hit3,
            "context_hit": context_hit,
            "elapsed_ms": elapsed_ms,
        })

        print(
            f"{q['id']}: "
            f"Hit@1={hit1}, "
            f"Hit@3={hit3}, "
            f"ContextHit={context_hit}"
        )

    return traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", choices=["dev", "test"], required=True
    )
    parser.add_argument(
        "--strategy",
        choices=["tfidf", "dense", "hybrid"],
        required=True
    )
    parser.add_argument("--chunk-strategy", default="A")
    parser.add_argument("--budget", type=int, default=800)
    args = parser.parse_args()

    path = ROOT / "benchmark" / "questions.json"

    with open(path, encoding="utf-8") as f:
        questions = json.load(f)

    selected = [
        q for q in questions
        if q["split"] == args.split
        and q.get("gold_source_id")
        and q.get("evidence_quote")
    ]

    if not selected:
        raise ValueError("Không tìm thấy câu hỏi có gold evidence")

    retrievers = {
        "tfidf": TfidfRetriever,
        "dense": DenseRetriever,
        "hybrid": HybridRetriever,
    }

    retriever = retrievers[args.strategy](
        strategy=args.chunk_strategy
    )

    traces = evaluate(
        retriever,
        selected,
        args.strategy,
        budget=args.budget
    )

    n = len(traces)

    summary = {
        "strategy": args.strategy,
        "chunk_strategy": args.chunk_strategy,
        "split": args.split,
        "n": n,
        "hit1": sum(t["hit1"] for t in traces),
        "hit3": sum(t["hit3"] for t in traces),
        "context_hit": sum(t["context_hit"] for t in traces),
        "hit1_rate": sum(t["hit1"] for t in traces) / n,
        "hit3_rate": sum(t["hit3"] for t in traces) / n,
        "context_hit_rate": sum(
            t["context_hit"] for t in traces
        ) / n,
        "avg_latency_ms": sum(
            t["elapsed_ms"] for t in traces
        ) / n,
    }

    output_dir = ROOT / "report" / "retrieval"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / (
        f"{args.strategy}_{args.split}.json"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": summary, "traces": traces},
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\n========== SUMMARY ==========")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nSaved to: {output_file}")


if __name__ == "__main__":
    main()
