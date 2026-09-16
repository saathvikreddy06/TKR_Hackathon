import sys
from pathlib import Path
import json
import os
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.cloud.firestore_v1.vector import Vector
from google.api_core.exceptions import ResourceExhausted
from app.firebase import db

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data/processed/local_knowledge_embeddings.jsonl"
CHECKPOINT = ROOT / "data/manifests/firestore_local_embeddings_checkpoint.json"
COLLECTION = "standard_chunks_local"

BATCH_SIZE = 100
MAX_RETRIES = 8

if db is None:
    raise RuntimeError("Firestore is not connected.")

os.makedirs(CHECKPOINT.parent, exist_ok=True)

completed = 0

if CHECKPOINT.exists():
    with open(CHECKPOINT, "r", encoding="utf-8") as f:
        completed = json.load(f).get("completed", 0)

with open(INPUT, "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

total = len(records)

if completed >= total:
    print(f"Upload already complete: {completed}/{total}")
    raise SystemExit

print(f"Resuming from {completed}/{total}")

for start in range(completed, total, BATCH_SIZE):
    batch_records = records[start:start + BATCH_SIZE]

    for attempt in range(MAX_RETRIES):
        try:
            batch = db.batch()

            for record in batch_records:
                ref = db.collection(COLLECTION).document(record["chunk_id"])

                batch.set(ref, {
                    "chunk_id": record["chunk_id"],
                    "document_id": record["document_id"],
                    "document_type": record["document_type"],
                    "text": record["text"],
                    "metadata": record.get("metadata", {}),
                    "embedding": Vector(record["embedding"])
                }, merge=True)

            batch.commit()
            break

        except ResourceExhausted:
            if attempt == MAX_RETRIES - 1:
                raise

            wait = min(60, 5 * (2 ** attempt))
            print(f"Quota reached. Waiting {wait}s...")
            time.sleep(wait)

    completed = start + len(batch_records)

    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump({
            "collection": COLLECTION,
            "dimensions": 384,
            "completed": completed,
            "total": total
        }, f, indent=2)

    print(f"Uploaded: {completed}/{total}")

print(f"Completed: {completed}/{total}")
print(f"Collection: {COLLECTION}")