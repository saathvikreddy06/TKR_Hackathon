import json
import time
from pathlib import Path

from google import genai
from google.genai import types
from google.cloud.firestore_v1.vector import Vector

from app.config import GEMINI_API_KEY
from app.firebase import db


DATA_FILE = Path("data/bis_rag_documents.json")

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

COLLECTION_NAME = "standard_chunks"

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_embedding(text):
    """Generate a 768-dimensional Gemini embedding."""

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSIONS
        )
    )

    return response.embeddings[0].values


def main():

    print("Loading RAG documents...")

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        documents = json.load(file)

    print(f"Found {len(documents)} documents.")

    collection = db.collection(COLLECTION_NAME)

    for index, document in enumerate(documents, start=1):

        standard_id = document["standard_id"]

        print(
            f"[{index}/{len(documents)}] "
            f"Processing {standard_id} "
            f"({document['standard_number']})..."
        )

        text = document["text"]

        embedding = generate_embedding(text)

        firestore_document = {
            "standard_id": standard_id,
            "standard_number": document["standard_number"],
            "part": document.get("part"),
            "section": document.get("section"),
            "year": document.get("year"),
            "title": document.get("title"),
            "product_category": document.get("product_category"),
            "industry": document.get("industry"),
            "scheme": document.get("scheme"),
            "mandatory_qco": document.get("mandatory_qco"),
            "status": document.get("status"),
            "source_url": document.get("source_url"),
            "document_url": document.get("document_url"),

            "text": text,

            "embedding": Vector(embedding)
        }

        collection.document(standard_id).set(
            firestore_document
        )

        print("   ✓ Stored in Firestore")

        # Small delay to avoid sending requests too rapidly.
        if index < len(documents):
            time.sleep(0.2)

    print()
    print("=" * 50)
    print("INGESTION COMPLETE")
    print("=" * 50)
    print(f"Documents processed: {len(documents)}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Embedding dimensions: {EMBEDDING_DIMENSIONS}")


if __name__ == "__main__":
    main()