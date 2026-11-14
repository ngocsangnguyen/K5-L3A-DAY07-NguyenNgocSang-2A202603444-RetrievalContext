
from dense_retriever import DenseRetriever
from tfidf_retriever import TfidfRetriever


class HybridRetriever:
    def __init__(self, strategy="A", rrf_k=60):
        self.dense = DenseRetriever(strategy=strategy)
        self.tfidf = TfidfRetriever(strategy=strategy)
        self.rrf_k = rrf_k

    def search(self, query, *, filters=None, top_k=3):
        # Lấy nhiều candidates trước khi fusion
        candidate_k = max(top_k * 5, 20)

        dense_hits = self.dense.search(
            query, filters=filters, top_k=candidate_k
        )
        tfidf_hits = self.tfidf.search(
            query, filters=filters, top_k=candidate_k
        )

        fused = {}

        for hits in (dense_hits, tfidf_hits):
            for rank, hit in enumerate(hits, start=1):
                chunk_id = hit["id"]

                if chunk_id not in fused:
                    fused[chunk_id] = {
                        **hit,
                        "score": 0.0,
                    }

                fused[chunk_id]["score"] += (
                    1.0 / (self.rrf_k + rank)
                )

        results = sorted(
            fused.values(),
            key=lambda x: (-x["score"], x["id"]),
        )

        return results[:top_k]
