from google import genai

from app.config import GEMINI_API_KEY


GENERATION_MODEL = "gemini-3.6-flash"

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_answer(query: str, retrieved_results: list):
    """
    Generate a BIS-grounded answer using retrieved standards.
    """

    if not retrieved_results:
        return {
            "answer": (
                "I could not find a relevant BIS standard in the available "
                "knowledge base."
            ),
            "sources": []
        }

    context_parts = []

    for i, result in enumerate(retrieved_results, start=1):

        context_parts.append(
            f"""
SOURCE {i}

Standard Number: {result.get("standard_number")}
Part: {result.get("part")}
Section: {result.get("section")}
Year: {result.get("year")}
Title: {result.get("title")}
Product Category: {result.get("product_category")}
Industry: {result.get("industry")}
Certification Scheme: {result.get("scheme")}
Mandatory QCO: {result.get("mandatory_qco")}
Status: {result.get("status")}

Details:
{result.get("text")}

BIS Document:
{result.get("document_url")}

Source:
{result.get("source_url")}
"""
        )

    context = "\n".join(context_parts)

    prompt = f"""
You are StandIQ, an intelligent assistant for Indian Standards
published by the Bureau of Indian Standards (BIS).

Answer the user's question using ONLY the retrieved BIS information
provided below.

IMPORTANT RULES:

1. Do not invent BIS standards, certification schemes, QCOs, dates,
   requirements, or testing parameters.

2. If the retrieved information does not contain enough information
   to answer the question, clearly say that the available BIS
   knowledge base does not contain sufficient information.

3. Prefer the most relevant retrieved standard.

4. If multiple standards are relevant, explain their relevance
   clearly.

5. Mention the exact IS number and year whenever available.

6. If certification scheme or mandatory QCO information is available,
   mention it.

7. Keep the answer concise and easy to understand.

8. Do not answer unrelated questions using general knowledge.
   StandIQ is specifically focused on BIS standards.

USER QUESTION:
{query}

RETRIEVED BIS INFORMATION:
{context}
"""

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    sources = []

    for result in retrieved_results:
        sources.append({
            "standard_number": result.get("standard_number"),
            "part": result.get("part"),
            "year": result.get("year"),
            "title": result.get("title"),
            "scheme": result.get("scheme"),
            "mandatory_qco": result.get("mandatory_qco"),
            "status": result.get("status"),
            "document_url": result.get("document_url"),
            "source_url": result.get("source_url"),
            "distance": result.get("distance")
        })

    return {
        "answer": response.text,
        "sources": sources
    }