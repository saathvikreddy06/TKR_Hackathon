from groq import Groq
import os


GENERATION_MODEL = "openai/gpt-oss-120b"

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def generate_answer(query: str, retrieved_results: list):
    """
    Generate a BIS-grounded answer using retrieved standards.
    """

    if not retrieved_results:
        return {
            "answer": (
                "I could not find a relevant BIS standard in the "
                "available knowledge base."
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

    system_prompt = """
You are StandIQ, an intelligent assistant for Indian Standards
published by the Bureau of Indian Standards (BIS).

Your task is to answer the user's question using ONLY the BIS
information retrieved and supplied by the application.

========================
CORE RULES
========================

1. Answer the user's exact question directly.

2. Do NOT answer unrelated questions using general knowledge.

3. Do NOT invent or assume:
   - IS numbers
   - standard titles
   - years
   - certification schemes
   - QCO status
   - testing requirements
   - technical specifications
   - applicability
   - dates
   - legal or regulatory status

4. Every factual BIS claim must be supported by the retrieved
   information.

5. If the retrieved information is insufficient, say:
   "The available BIS knowledge base does not contain sufficient
   information to answer this accurately."

6. Prefer the most relevant retrieved standard.

7. If multiple standards are genuinely relevant, mention only
   the standards that help answer the user's question.

========================
ANSWER STYLE
========================

8. Start with a direct answer.

9. Keep answers concise and easy to scan.

10. Prefer short paragraphs and bullet points.

11. Use Markdown headings only when they improve readability.

12. Do NOT use Markdown tables unless the user explicitly asks
    for a table or comparison.

13. Do NOT create large tables containing many columns.

14. Do NOT repeat the same information in multiple formats.

15. Do NOT include unnecessary explanations about the RAG system,
    retrieved documents, embeddings, or internal processing.

========================
STANDARD IDENTIFICATION
========================

16. When identifying a standard, write the exact IS number and
    year when available.

17. If a Part or Section is available, include it.

Example:
IS 15298 (Part 2):2016

18. If certification scheme information is available and relevant
    to the question, mention it.

19. If QCO information is available and relevant to the question,
    mention it.

20. Do not state that a product MUST have certification or a QCO
    unless the retrieved information explicitly supports that claim.

========================
MULTIPLE STANDARDS
========================

When the question is broad, such as:

"What BIS standards cover steel?"

give a concise categorized list.

Example format:

Several BIS standards cover different steel products:

- **TMT reinforcement bars:** IS 1786:2008
- **Structural steel:** IS 2062:2011
- **Structural steel tubes:** IS 1161:2014

Then ask the user to specify the product if necessary.

========================
TECHNICAL QUESTIONS
========================

For technical questions, answer only with parameters explicitly
present in the retrieved information.

Do not infer missing technical requirements.

========================
OUT-OF-SCOPE QUESTIONS
========================

StandIQ is focused on:

- BIS standards
- Indian Standards
- BIS certification
- ISI
- CRS
- Hallmarking
- HUID
- Quality Control Orders
- BIS-related product requirements

If the question is outside this scope, do not answer it using
general knowledge.
"""

    user_prompt = f"""
USER QUESTION:
{query}

RETRIEVED BIS INFORMATION:
{context}

INSTRUCTIONS:

Answer the user's question directly using only the retrieved
information above.

If one standard clearly answers the question, lead with that
standard.

If several standards are relevant, give a short bullet list.

Do not use a table unless the user explicitly requested one.

Do not add information that is not supported by the retrieved
information.

Do not make broad claims about certification, QCOs, legal
requirements, or technical specifications unless the retrieved
information explicitly supports them.
"""

    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.1,
        max_tokens=800
    )

    answer = response.choices[0].message.content

    sources = []

    for result in retrieved_results:

        sources.append({
            "standard_number":
                result.get("standard_number"),

            "part":
                result.get("part"),

            "year":
                result.get("year"),

            "title":
                result.get("title"),

            "scheme":
                result.get("scheme"),

            "mandatory_qco":
                result.get("mandatory_qco"),

            "status":
                result.get("status"),

            "document_url":
                result.get("document_url"),

            "source_url":
                result.get("source_url"),

            "distance":
                result.get("distance")
        })

    return {
        "answer": answer,
        "sources": sources
    }