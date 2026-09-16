import hashlib
import json
import re
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

INPUT = DATA / "processed/knowledge_documents.json"
OUTPUT = DATA / "processed/knowledge_chunks.json"
MANIFEST = DATA / "manifests/knowledge_chunks_manifest.json"

CHARS_PER_CHUNK = 3000
OVERLAP = 400


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def chunk_text(text):
    text = clean(text)

    if len(text) <= CHARS_PER_CHUNK:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHARS_PER_CHUNK, len(text))

        if end < len(text):
            boundary = text.rfind(". ", start + CHARS_PER_CHUNK // 2, end)

            if boundary == -1:
                boundary = text.rfind(" - ", start + CHARS_PER_CHUNK // 2, end)

            if boundary == -1:
                boundary = text.rfind(" ", start + CHARS_PER_CHUNK // 2, end)

            if boundary > start:
                end = boundary + 1

        piece = text[start:end].strip()

        if piece:
            chunks.append(piece)

        if end >= len(text):
            break

        start = max(end - OVERLAP, start + 1)

    return chunks


def make_id(document_id, index, text):
    value = f"{document_id}|{index}|{text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def main():
    data = load(INPUT)
    documents = data.get("documents", [])

    chunks = []
    seen = set()

    for document in documents:
        document_id = document.get("document_id")

        if not document_id:
            continue

        text = document.get("text", "")
        parts = chunk_text(text)

        for index, part in enumerate(parts):
            chunk_id = make_id(document_id, index, part)

            if chunk_id in seen:
                continue

            seen.add(chunk_id)

            chunk = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "document_type": document.get("document_type"),
                "standard_id": document.get("standard_id"),
                "standard_number": document.get("standard_number"),
                "title": document.get("title"),
                "product": document.get("product"),
                "lab_name": document.get("lab_name"),
                "lab_code": document.get("lab_code"),
                "source": document.get("source"),
                "source_url": document.get("source_url"),
                "chunk_index": index,
                "chunk_count": len(parts),
                "text": part
            }

            chunks.append(chunk)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(chunks),
        "chunk_size": CHARS_PER_CHUNK,
        "overlap": OVERLAP,
        "chunks": chunks
    }

    temp = OUTPUT.with_suffix(".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    temp.replace(OUTPUT)

    manifest = {
        "generated_at": result["generated_at"],
        "source_documents": len(documents),
        "chunks": len(chunks),
        "chunk_size": CHARS_PER_CHUNK,
        "overlap": OVERLAP,
        "sha256": hashlib.sha256(
            OUTPUT.read_bytes()
        ).hexdigest()
    }

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Source documents: {len(documents)}")
    print(f"Chunks: {len(chunks)}")
    print(f"Output: {OUTPUT}")
    print(f"Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
