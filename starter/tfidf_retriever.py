import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TfidfRetriever:
    def __init__(self, strategy="A"):
        day6_root = Path(os.environ["DAY6_ROOT"])
        load_dotenv(day6_root / ".env", override=True)

        self.strategy = strategy

        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            rows = conn.execute(
                """
                SELECT chunk_id, document_id, source,
                       page, content, metadata
                FROM ingestion_chunks
                WHERE strategy = %s
                ORDER BY chunk_id
                """,
                (strategy,),
            ).fetchall()

        self.chunks = [
            {
                "id": row[0],
                "source_id": row[1],
                "source": row[2],
                "page": row[3],
                "text": row[4],
                "metadata": row[5],
            }
            for row in rows
        ]

        if not self.chunks:
            raise ValueError(f"No chunks found for strategy {strategy}")

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            stop_words="english",
        )

        self.matrix = self.vectorizer.fit_transform(
            [chunk["text"] for chunk in self.chunks]
        )

    def search(self, query, *, filters=None, top_k=3):
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix)[0]

        results = []

        for idx in scores.argsort()[::-1]:
            chunk = self.chunks[idx]

            if filters and not all(
                chunk["metadata"].get(k) == v
                for k, v in filters.items()
            ):
                continue

            results.append({
                **chunk,
                "score": float(scores[idx]),
            })

            if len(results) >= top_k:
                break

        return results