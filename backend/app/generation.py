from groq import Groq
import os
import re

from dotenv import load_dotenv
from app.language import get_language_instruction


load_dotenv()

GENERATION_MODEL = "openai/gpt-oss-120b"

api_key = os.getenv("GROQ_API_KEY") or os.getenv("API_KEY")
client = Groq(api_key=api_key) if api_key else None


def answer_matches_language(answer: str, language: str) -> bool:
    if language == "te":
        return bool(re.search(r"[\u0c00-\u0c7f]", answer))

    if language == "hi":
        return bool(re.search(r"[\u0900-\u097f]", answer))

    return True


def generate_answer(
    query: str,
    retrieved_results: list,
    language: str = "en"
):
    """
    Generate a BIS-grounded answer using retrieved standards.
    """

    if not client:
        return {
            "answer": "GROQ_API_KEY is not configured on backend server.",
            "sources": []
        }

    if not retrieved_results:
        no_evidence_messages = {
            "te": (
                "అందుబాటులో ఉన్న BIS knowledge base ఈ ప్రశ్నకు "
                "ఖచ్చితంగా సమాధానం ఇవ్వడానికి సరిపడ సమాచారం కలిగి లేదు."
            ),
            "hi": (
                "उपलब्ध BIS knowledge base में इस प्रश्न का सही "
                "उत्तर देने के लिए पर्याप्त जानकारी नहीं है।"
            ),
        }

        return {
            "answer": no_evidence_messages.get(
                language,
                (
                    "I could not find a relevant BIS standard in the "
                    "available knowledge base."
                )
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

    language_name = {
        "en": "English",
        "te": "Telugu",
        "hi": "Hindi",
    }.get(language, "English")

    system_prompt = f"""
You are StandIQ, an intelligent assistant for Indian Standards
published by the Bureau of Indian Standards (BIS).

{get_language_instruction(language)}

FINAL LANGUAGE RULE (HIGHEST PRIORITY):

The user's language is {language_name} ({language}).

Write the complete final answer in {language_name}.

Do not answer in English when the language is Telugu or Hindi.

Translate explanatory sentences naturally even though the retrieved
BIS evidence below may be in English.

Keep standard numbers, years, URLs, and technical identifiers
in their original form.

For Telugu, a valid answer style is:
"ఈ ఉత్పత్తికి సంబంధించిన BIS ప్రమాణం IS 2347:2017."

For Hindi, a valid answer style is:
"इस उत्पाद से संबंधित BIS मानक IS 2347:2017 है।"

Supported languages are English, Telugu, and Hindi.

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

5. If the retrieved information is insufficient, say this clearly
   in the user's language.

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

Answer-language requirement:

{get_language_instruction(language)}

Return only the answer in {language_name}.

Do not add an English translation or language explanation.

Keep standard numbers, years, official BIS names, source URLs,
and technical identifiers exactly as provided in the retrieved
information.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=800
    )

    answer = response.choices[0].message.content

    # Verify that Telugu/Hindi responses actually contain
    # characters from the requested script.
    if not answer_matches_language(answer, language):
        retry_messages = messages + [
            {
                "role": "user",
                "content": (
                    f"Your previous draft was not written in "
                    f"{language_name}. Rewrite the complete answer "
                    f"in natural {language_name} now. "
                    "Do not include any English translation. "
                    "Preserve all IS numbers, years, URLs, and "
                    "technical identifiers exactly."
                )
            }
        ]

        retry_response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=retry_messages,
            temperature=0.1,
            max_tokens=800
        )

        answer = retry_response.choices[0].message.content

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
        "answer": answer,
        "sources": sources
    }