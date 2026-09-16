import json
import os
import time
from sentence_transformers import SentenceTransformer

INPUT = "backend/data/processed/embedding_chunks.json"
OUTPUT = "backend/data/processed/local_knowledge_embeddings.jsonl"
CHECKPOINT = "backend/data/manifests/local_knowledge_embeddings_checkpoint.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE = 32

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
os.makedirs(os.path.dirname(CHECKPOINT), exist_ok=True)

with open(INPUT, "r", encoding="utf-8") as f:
    chunks = json.load(f)["chunks"]

completed = 0

if os.path.exists(CHECKPOINT):
    with open(CHECKPOINT, "r", encoding="utf-8") as f:
        completed = json.load(f).get("completed", 0)

if completed >= len(chunks):
    print(f"Embedding already complete: {completed}/{len(chunks)}")
    raise SystemExit

model = SentenceTransformer(MODEL_NAME)

mode = "a" if completed > 0 else "w"

with open(OUTPUT, mode, encoding="utf-8") as out:
    start_time = time.time()

    for start in range(completed, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        texts = [item["text"] for item in batch]

        embeddings = model.encode(
            texts,
            batch_size=BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        for item, embedding in zip(batch, embeddings):
            record = {
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "document_type": item["document_type"],
                "text": item["text"],
                "metadata": item.get("metadata", {}),
                "embedding": embedding.tolist()
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

        out.flush()

        completed = start + len(batch)

        with open(CHECKPOINT, "w", encoding="utf-8") as f:
            json.dump({
                "model": MODEL_NAME,
                "dimensions": int(embeddings.shape[1]),
                "completed": completed,
                "total": len(chunks)
            }, f, indent=2)

        elapsed = time.time() - start_time
        rate = (completed - json.load(open(CHECKPOINT, encoding="utf-8")).get("initial_completed", 0)) / elapsed if elapsed > 0 else 0

        print(f"Progress: {completed}/{len(chunks)}")

print(f"Completed: {completed}/{len(chunks)}")
print(f"Output: {OUTPUT}")
print(f"Checkpoint: {CHECKPOINT}")