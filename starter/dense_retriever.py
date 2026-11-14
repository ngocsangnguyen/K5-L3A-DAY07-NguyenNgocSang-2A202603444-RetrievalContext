
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Trỏ tới thư mục gốc của Day 6
DAY6_ROOT = Path(os.environ["DAY6_ROOT"]).resolve()
sys.path.insert(0, str(DAY6_ROOT / "starter"))

from src.embeddings import MyEmbedder
from src.store import PgVectorStore


class DenseRetriever:
    def __init__(self, strategy="A"):
        load_dotenv(DAY6_ROOT / ".env")

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL chưa được cấu hình")

        self.strategy = strategy
        self.embedder = MyEmbedder(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.store = PgVectorStore(
            database_url,
            self.embedder.dimensions
        )

    def search(self, query, *, filters=None, top_k=3):
        vector = self.embedder.embed_query(query)

        rows = self.store.search(
            self.strategy,
            vector,
            top_k=top_k,
            filters=filters
        )

        return [
            {
                "id": row["chunk_id"],
                "source_id": row["document_id"],
                "source": row["source"],
                "page": row["page"],
                "text": row["text"],
                "metadata": row["metadata"],
                "score": row["score"],
            }
            for row in rows
        ]
