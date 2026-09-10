from google import genai
from google.genai import types
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from app.config import GEMINI_API_KEY
from app.firebase import db


EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_query_embedding(query: str):
    """Generate a 768-dimensional embedding for a user query."""

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSIONS
        )
    )

    return response.embeddings[0].values


def search_standards(query: str, limit: int = 10):
    """Find the most semantically similar BIS standards."""

    query_embedding = generate_query_embedding(query)

    vector_query = (
        db.collection("standard_chunks")
        .find_nearest(
            vector_field="embedding",
            query_vector=query_embedding,
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
            distance_result_field="vector_distance"
        )
    )

    results = vector_query.stream()

    matches = []

    for document in results:
        data = document.to_dict()

        matches.append({
            "id": document.id,
            "standard_id": data.get("standard_id"),
            "standard_number": data.get("standard_number"),
            "part": data.get("part"),
            "section": data.get("section"),
            "year": data.get("year"),
            "title": data.get("title"),
            "product_category": data.get("product_category"),
            "industry": data.get("industry"),
            "scheme": data.get("scheme"),
            "mandatory_qco": data.get("mandatory_qco"),
            "status": data.get("status"),
            "text": data.get("text"),
            "source_url": data.get("source_url"),
            "document_url": data.get("document_url"),
            "distance": data.get("vector_distance")
        })

    return matches