
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from agentic import run_agent
from dense_retriever import DenseRetriever
from tfidf_retriever import TfidfRetriever
from hybrid_retriever import HybridRetriever
from llm_controller import LLMController


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--question",
        default="What is an algorithm?",
    )
    parser.add_argument(
        "--retriever",
        choices=["dense", "tfidf", "hybrid"],
        default="hybrid",
    )
    parser.add_argument("--max-searches", type=int, default=4)
    args = parser.parse_args()

    day6_root = Path(os.environ["DAY6_ROOT"])

    # Nạp cấu hình PostgreSQL Day 6
    load_dotenv(day6_root / ".env", override=True)

    # Nạp cấu hình OpenRouter Day 7
    day7_env = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(day7_env, override=True)
    retrievers = {
        "dense": DenseRetriever,
        "tfidf": TfidfRetriever,
        "hybrid": HybridRetriever,
    }

    # Khởi tạo Controller trước để giữ cấu hình OpenRouter Day 7
    controller = LLMController()

    print("Controller URL:", controller.base_url)
    print("Controller model:", controller.model)

    retriever = retrievers[args.retriever](strategy="A")

    result = run_agent(
        args.question,
        controller,
        retriever,
        max_searches=args.max_searches,
        top_k=3,
        budget=800,
    )

    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
