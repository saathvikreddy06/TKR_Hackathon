import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
EMBEDDINGS_FILE = ROOT / "data/processed/local_knowledge_embeddings.jsonl"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class LocalRetriever:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.records = []

        with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                self.records.append(json.loads(line))

        self.embeddings = np.array(
            [record["embedding"] for record in self.records],
            dtype=np.float32
        )

    def search(self, query, limit=8):
        query_embedding = self.model.encode(
            query,
            normalize_embeddings=True
        )

        scores = self.embeddings @ query_embedding
        indices = np.argsort(scores)[::-1][:limit]

        results = []

        for index in indices:
            record = self.records[index]

            results.append({
                "chunk_id": record["chunk_id"],
                "document_id": record["document_id"],
                "document_type": record["document_type"],
                "text": record["text"],
                "metadata": record.get("metadata", {}),
                "score": float(scores[index])
            })

        return results


if __name__ == "__main__":
    retriever = LocalRetriever()

    query = "What is the applicable BIS standard for LED luminaires?"
    results = retriever.search(query, limit=5)

    print("\nQuery:", query)
    print("\nTop results:\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['score']:.4f}")
        print(f"   Type: {result['document_type']}")
        print(f"   Chunk: {result['chunk_id']}")
        print(f"   Text: {result['text'][:500]}")
        print()