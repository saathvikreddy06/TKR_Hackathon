from groq import Groq
import logging
import os
import re

from dotenv import load_dotenv
from app.language import get_language_instruction, get_semantic_translation_guidance


load_dotenv()

GENERATION_MODEL = "openai/gpt-oss-120b"

api_key = os.getenv("GROQ_API_KEY") or os.getenv("API_KEY")
client = Groq(api_key=api_key) if api_key else None
logger = logging.getLogger(__name__)


OFFICIAL_IDENTIFIER_RE = re.compile(
    r"(?:https?://\S+|\b(?:IS|BIS|ISI|QCO)(?:[-/()\w.:]*)|"
    r"\bScheme[- ]?(?:I|II|[0-9]+)\b|\b[A-Z]{2,}[A-Z0-9-]*\b|\b\d[\w./:-]*\b)"
)

TRANSLITERATION_PATTERNS = {
    "te": re.compile(
        r"(?:హై\s+స్ట్రెంగ్త్|స్ట్రెంగ్త్|డీఫార్మ్డ్|బార్స్|వైర్స్|"
        r"రీ.?ఇన్ఫోర్స్|రీఇన్ఫోర్స్|స్పెసిఫికేషన్|సర్టిఫికేషన్|"
        r"కన్స్ట్రక్షన్|ఇన్.?ఫ్రాస్ట్రక్చర్|మాండేటరీ|టెన్సైల్\s+స్ట్రెంగ్త్|"
        r"ఫ్రాక్చర్|ఎలాంగేషన్|రేషియో|ప్రూఫ్\s+స్ట్రెస్|యీల్డ్\s+స్ట్రెంగ్త్)",
        re.IGNORECASE,
    ),
    "hi": re.compile(
        r"(?:हाई\s+स्ट्रेंथ|स्ट्रेंथ|डीफॉर्म्ड|बार्स|वायर्स|"
        r"री.?इन्फोर्स|रीइन्फोर्स|स्पेसिफिकेशन|सर्टिफिकेशन|"
        r"कंस्ट्रक्शन|इन्फ्रास्ट्रक्चर|मैंडेटरी|टेनसाइल\s+स्ट्रेंथ|"
        r"फ्रैक्चर|एलोंगेशन|रेशियो|प्रूफ\s+स्ट्रेस|यील्ड\s+स्ट्रेंथ)",
        re.IGNORECASE,
    ),
}

SEMANTIC_TERM_REPLACEMENTS = {
    "te": (
        (r"రీ.?ఇన్ఫోర్స్‌?మెంట్", "ఉపబలం"),
        (r"రీఇన్ఫోర్స్‌?మెంట్", "ఉపబలం"),
        (r"సర్టిఫికేషన్", "ధృవీకరణ"),
        (r"కన్స్ట్రక్షన్", "నిర్మాణం"),
        (r"ఇన్.?ఫ్రాస్ట్రక్చర్", "మౌలిక సదుపాయాలు"),
        (r"మాండేటరీ", "తప్పనిసరి"),
        (r"టెన్సైల్\s+స్ట్రెంగ్త్", "తన్యతా బలం"),
        (r"యీల్డ్\s+స్ట్రెంగ్త్", "యీల్డ్ బలం"),
        (r"ప్రూఫ్\s+స్ట్రెస్", "నిరూపిత ఒత్తిడి"),
        (r"డీఫార్మ్డ్", "వికృత"),
        (r"స్టీల్", "ఉక్కు"),
    ),
    "hi": (
        (r"री.?इन्फोर्समेंट", "सुदृढ़ीकरण"),
        (r"सर्टिफिकेशन", "प्रमाणन"),
        (r"कंस्ट्रक्शन", "निर्माण"),
        (r"इन्फ्रास्ट्रक्चर", "बुनियादी ढाँचा"),
        (r"मैंडेटरी", "अनिवार्य"),
        (r"टेनसाइल\s+स्ट्रेंथ", "तन्यता शक्ति"),
        (r"यील्ड\s+स्ट्रेंथ", "उपज शक्ति"),
        (r"प्रूफ\s+स्ट्रेस", "प्रूफ तनाव"),
        (r"डीफॉर्म्ड", "विकृत"),
        (r"स्टील", "इस्पात"),
    ),
}


def normalize_semantic_terms(answer: str, language: str) -> str:
    """Replace recurring phonetic technical terms with semantic equivalents."""

    for pattern, replacement in SEMANTIC_TERM_REPLACEMENTS.get(language, ()):
        answer = re.sub(pattern, replacement, answer, flags=re.IGNORECASE)
    return answer


def answer_matches_language(answer: str, language: str) -> bool:
    if language == "en":
        return True

    script_pattern = r"[\u0c00-\u0c7f]" if language == "te" else r"[\u0900-\u097f]"
    if not re.search(script_pattern, answer):
        return False

    transliterated_terms = TRANSLITERATION_PATTERNS.get(language)
    if transliterated_terms and len(transliterated_terms.findall(answer)) >= 2:
        return False

    content = OFFICIAL_IDENTIFIER_RE.sub(" ", answer)
    script_count = len(re.findall(script_pattern, content))
    latin_count = len(re.findall(r"[A-Za-z]", content))
    total_letters = script_count + latin_count

    if total_letters == 0:
        return False

    return script_count / total_letters >= 0.6


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

    fallback_messages = {
        "te": "సమాధానాన్ని రూపొందించలేకపోయాము. దయచేసి మళ్లీ ప్రయత్నించండి.",
        "hi": "उत्तर तैयार नहीं किया जा सका। कृपया फिर से प्रयास करें।",
        "en": "I could not generate an answer. Please try again.",
    }

    if not retrieved_results:
        no_evidence_messages = {
            "te": (
                "అందుబాటులో ఉన్న BIS జ్ఞాన ఆధారంలో ఈ ప్రశ్నకు ఖచ్చితమైన "
                "సమాధానం ఇవ్వడానికి సరిపడ సమాచారం లేదు."
            ),
            "hi": (
                "उपलब्ध BIS ज्ञान आधार में इस प्रश्न का सही उत्तर देने के लिए "
                "पर्याप्त जानकारी नहीं है।"
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

SEMANTIC TRANSLATION POLICY:
{get_semantic_translation_guidance(language)}

FINAL LANGUAGE RULE (HIGHEST PRIORITY):

The user's language is {language_name} ({language}).

The selected output language controls the ENTIRE response. Write the complete
final answer in {language_name}, regardless of the language used in the user
question.

Do not answer in English when the language is Telugu or Hindi.

Translate every explanatory sentence, heading, bullet point, standard title,
and description naturally even though the retrieved BIS evidence may be in
English. Do not copy English explanatory text from the sources.

Keep standard numbers, years, URLs, and technical identifiers
in their original form.

Only preserve official identifiers such as IS standard numbers, BIS, ISI, QCO,
Scheme-I, Scheme-II, URLs, and official codes. Standard titles are not
identifiers and must be translated.

For Telugu, a valid answer style is:
"ఈ ఉత్పత్తికి సంబంధించిన BIS ప్రమాణం IS 2347:2017."

For Hindi, a valid answer style is:
"इस उत्पाद से संबंधित BIS मानक IS 2347:2017 है।"

Supported languages are English, Telugu, and Hindi.

Your task is to answer the user's question using ONLY the BIS
information retrieved and supplied by the application.

The following context comes from authoritative BIS records. Titles and
descriptions may be in English because that is how they are stored. Do not
copy those English titles into a Telugu or Hindi answer. Translate their
meaning naturally and preserve only official identifiers.

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

STRICT ANSWER-LANGUAGE REQUIREMENT:

{get_language_instruction(language)}

Return only the answer in {language_name}.

Do not add an English translation or language explanation. Do not leave English
headings, standard titles, descriptions, recommendations, or conclusions.

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

    answer = (response.choices[0].message.content or "").strip()

    # Verify that Telugu/Hindi responses actually contain
    # characters from the requested script.
    if not answer_matches_language(answer, language):
        retry_messages = messages + [
            {
                "role": "user",
                "content": (
                    f"The previous response violated the selected language "
                    f"requirement. Rewrite the entire answer in {language_name}. "
                    "Translate all English explanatory text, BIS titles, "
                    "descriptions, headings, bullets, and conclusions. Do not "
                    "leave English explanatory sentences. Preserve only IS "
                    "standard numbers, BIS, ISI, QCO, Scheme-I, Scheme-II, "
                    "URLs, and official codes. Do not transliterate English "
                    "pronunciation into the target script; translate the "
                    "meaning naturally. For the title 'High Strength Deformed "
                    "Steel Bars and Wires for Concrete Reinforcement - "
                    "Specification', use the meaning 'కాంక్రీట్‌లో ఉపబలానికి "
                    "ఉపయోగించే అధిక బలం కలిగిన డీఫార్మ్డ్ స్టీల్ బార్లు మరియు "
                    "వైర్లకు సంబంధించిన ప్రమాణం' in Telugu, or 'कंक्रीट में "
                    "सुदृढ़ीकरण के लिए उच्च शक्ति वाले विकृत स्टील बार और वायर "
                    "से संबंधित मानक' in Hindi. Do not use phonetic forms such "
                    "as हाई/హై स्ट्रेंथ or रीइन्फोर्समेंट/రీఇన్ఫోర్స్‌మెంట్. "
                    "Return only the corrected answer."
                )
            }
        ]

        retry_response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=retry_messages,
            temperature=0.1,
            max_tokens=800
        )

        retry_answer = (retry_response.choices[0].message.content or "").strip()
        if retry_answer:
            answer = retry_answer

        if not answer_matches_language(answer, language):
            logger.warning(
                "Generated answer did not match requested language after retry: %s",
                language,
            )

    answer = normalize_semantic_terms(answer, language)

    if not answer:
        logger.warning("Generation returned empty content for language: %s", language)
        answer = fallback_messages.get(language, fallback_messages["en"])

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