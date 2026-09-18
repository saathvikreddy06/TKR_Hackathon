import os
import re

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


OFFICIAL_IDENTIFIER_RE = re.compile(
    r'\b(?:IS|ISO|IEC|BIS|QCO|LAB|LIMS)[\s\-:/]*[A-Z0-9()./\-]+\b',
    re.IGNORECASE
)


def result_type(item):
    match_type = item.get("match_type", "")

    if match_type == "lims_test":
        return "testing"

    if match_type == "lims_lab":
        return "laboratory"

    if match_type == "qco_relationship":
        return "qco"

    return item.get("document_type") or "standard"

def normalize_text(text):
    """
    Normalize retrieved/generated text and repair UTF-8 mojibake.

    The repair is intentionally applied before the BIS-specific cleanup.
    It handles both normal mojibake (for example, "â¯") and text that has
    been accidentally mojibaked more than once.
    """
    if not text:
        return ""

    text = str(text)

    # Repair one or more layers of UTF-8 text that were decoded as Latin-1.
    # Only apply the conversion when it produces valid UTF-8 and does not
    # make the text worse.
    for _ in range(3):
        try:
            repaired = text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break

        if repaired == text:
            break

        bad_before = sum(
            text.count(marker)
            for marker in (
                "\u00c3", "\u00c2", "\u00e2", "\u00f0"
            )
        )
        bad_after = sum(
            repaired.count(marker)
            for marker in (
                "\u00c3", "\u00c2", "\u00e2", "\u00f0"
            )
        )

        if bad_after > bad_before:
            break

        text = repaired

    # Common mojibake fallbacks. These use Unicode escapes so the source
    # file itself cannot become corrupted when copied between terminals.
    replacements = {
        "\u00e2\u00af": " ",
        "\u00c2\u00b1": "\u00b1",
        "\u00e2\u0080\u0093": "\u2013",
        "\u00e2\u0080\u0094": "\u2014",
        "\u00e2\u0080\u0098": "\u2018",
        "\u00e2\u0080\u0099": "\u2019",
        "\u00e2\u0080\u009c": "\u201c",
        "\u00e2\u0080\u009d": "\u201d",
        "\u00e2\u0080\u00a6": "\u2026",
        "\u00e2\u0086\u0092": "\u2192",
        "\u00e2\u0086\u0090": "\u2190",
        "\u00c3\u0097": "\u00d7",
        "\u00c3\u00b7": "\u00f7",
        "\u00c3\u00a9": "\u00e9",
        "\u00c3\u00a8": "\u00e8",
        "\u00c3\u00a2": "\u00e2",
        "\u00c3\u00a4": "\u00e4",
        "\u00c3\u00b6": "\u00f6",
        "\u00c3\u00bc": "\u00fc",
        "\u00c2": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Common BIS/OCR patterns where only the leading mojibake character
    # remains after partial corruption.
    text = text.replace("\u00e2 Chemical", " - Chemical")
    text = text.replace("\u00e2 Physical", " - Physical")
    text = text.replace("\u00e2 Requirements", " - Requirements")
    text = text.replace("\u00e2 requirement", " - requirement")
    text = text.replace("\u00e2 Table", " - Table")
    text = text.replace("\u00e2 Clause", " - Clause")
    text = text.replace("\u00e2 IS", " - IS")

    # Standalone corrupted dash/non-breaking-space markers.
    text = re.sub(r"\u00e2(?=\d)", " ", text)
    text = re.sub(r"(?<=\d)\u00e2(?=\s)", " ", text)
    text = re.sub(r"\u00e2(?=\()", " ", text)
    text = re.sub(r"\u00e2(?=\|)", " ", text)
    text = re.sub(r"\u00e2(?=\n)", " ", text)

    # Chemical formula cleanup.
    text = re.sub(r"\bSO\u00e2\b", "SO\u2083", text)

    # Remove residual UTF-8 mojibake byte prefixes when safe.
    text = re.sub(
        r"[\u00c2\u00c3][\u0080-\u00bf]",
        "",
        text
    )

    # Clean repeated whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_clause_number(query):
    match = re.search(
        r'\bclause\s*(?:no\.?|number)?\s*(\d+(?:\.\d+)?)',
        query,
        re.IGNORECASE
    )

    return match.group(1) if match else None


def build_standard_context(standards):
    if not standards:
        return ""

    lines = ["STANDARD INFORMATION:"]

    for item in standards[:8]:
        standard_number = normalize_text(
            item.get("standard_number")
            or item.get("is_number")
            or ""
        )

        title = normalize_text(
            item.get("title")
            or item.get("name")
            or item.get("product")
            or ""
        )

        description = normalize_text(
            item.get("description")
            or ""
        )

        status = normalize_text(
            item.get("status")
            or ""
        )

        parts = []

        if standard_number:
            parts.append(
                f"Standard: {standard_number}"
            )

        if title:
            parts.append(
                f"Title: {title}"
            )

        if description:
            parts.append(
                f"Description: {description[:1000]}"
            )

        if status:
            parts.append(
                f"Status: {status}"
            )

        if parts:
            lines.append(" | ".join(parts))

    return "\n".join(lines)


def build_testing_context(tests, query=""):
    if not tests:
        return ""

    lines = ["BIS LIMS TESTING INFORMATION:"]

    requested_clause = extract_clause_number(query)

    added = 0

    for item in tests:
        if added >= 8:
            break

        standard_number = normalize_text(
            item.get("standard_number")
            or item.get("indian_standard_no")
            or item.get("is_number")
            or ""
        )

        product = normalize_text(
            item.get("product")
            or ""
        )

        designation = normalize_text(
            item.get("designation")
            or ""
        )

        lab_name = normalize_text(
            item.get("lab_name")
            or ""
        )

        lab_code = normalize_text(
            item.get("lab_code")
            or ""
        )

        charge = item.get("testing_charge")

        raw = normalize_text(
            item.get("testing_charge_raw")
            or item.get("test_method")
            or item.get("description")
            or ""
        )

        if requested_clause:
            clause_text = raw.lower()
            clause_number = requested_clause.lower()

            if (
                clause_number not in clause_text
                and f"clause {clause_number}" not in clause_text
                and f"cl. {clause_number}" not in clause_text
            ):
                continue

        parts = []

        if standard_number:
            parts.append(
                f"Standard: {standard_number}"
            )

        if product:
            parts.append(
                f"Product: {product}"
            )

        if designation:
            parts.append(
                f"Designation: {designation}"
            )

        if lab_name:
            parts.append(
                f"Laboratory: {lab_name}"
            )

        if lab_code:
            parts.append(
                f"Lab code: {lab_code}"
            )

        if charge is not None:
            parts.append(
                f"Testing charge: ₹{charge}"
            )

        if raw:
            parts.append(
                f"Testing details: {raw[:1600]}"
            )

        if parts:
            lines.append(
                " | ".join(parts)
            )

            added += 1

    return "\n".join(lines)


def build_lab_context(tests):
    if not tests:
        return ""

    lines = ["BIS LABORATORY INFORMATION:"]

    seen = set()

    for item in tests[:8]:
        lab_code = normalize_text(
            item.get("lab_code") or ""
        )

        lab_name = normalize_text(
            item.get("lab_name") or ""
        )

        if not lab_name:
            continue

        key = (
            lab_code,
            lab_name
        )

        if key in seen:
            continue

        seen.add(key)

        if lab_code:
            lines.append(
                f"Laboratory: {lab_name} | "
                f"Lab code: {lab_code}"
            )
        else:
            lines.append(
                f"Laboratory: {lab_name}"
            )

    return "\n".join(lines)


def build_qco_context(qcos):
    if not qcos:
        return ""

    lines = ["BIS QCO INFORMATION:"]

    for item in qcos[:8]:
        standard_number = normalize_text(
            item.get("standard_number")
            or ""
        )

        qco_document_id = normalize_text(
            item.get("qco_document_id")
            or ""
        )

        relationship = normalize_text(
            item.get("relationship")
            or ""
        )

        evidence = normalize_text(
            item.get("evidence")
            or ""
        )

        confidence = normalize_text(
            item.get("confidence")
            or ""
        )

        matched = item.get(
            "matched_is_numbers"
        ) or []

        matched_text = ", ".join(
            normalize_text(str(x))
            for x in matched
        )

        parts = []

        if standard_number:
            parts.append(
                f"Standard: {standard_number}"
            )

        if qco_document_id:
            parts.append(
                f"QCO document: {qco_document_id}"
            )

        if relationship:
            parts.append(
                f"Relationship: {relationship}"
            )

        if matched_text:
            parts.append(
                f"Matched IS numbers: {matched_text}"
            )

        if confidence:
            parts.append(
                f"Confidence: {confidence}"
            )

        if evidence:
            parts.append(
                f"Evidence: {evidence[:1200]}"
            )

        if parts:
            lines.append(
                " | ".join(parts)
            )

    return "\n".join(lines)


def build_context(hybrid_results, query=""):
    intent = hybrid_results.get("intent")

    sections = []

    if intent == "testing":
        testing = build_testing_context(
            hybrid_results.get("tests", []),
            query
        )

        if testing:
            sections.append(testing)

        standards = build_standard_context(
            hybrid_results.get(
                "exact_standards",
                []
            )
        )

        if standards:
            sections.append(
                "BIS STANDARD METADATA:\n"
                + standards
            )

    elif intent == "laboratory":
        labs = build_lab_context(
            hybrid_results.get("labs", [])
        )

        if labs:
            sections.append(labs)

        standards = build_standard_context(
            hybrid_results.get(
                "exact_standards",
                []
            )
        )

        if standards:
            sections.append(
                "BIS STANDARD METADATA:\n"
                + standards
            )

    elif intent == "qco":
        qco = build_qco_context(
            hybrid_results.get("qco", [])
        )

        if qco:
            sections.append(qco)

        standards = build_standard_context(
            hybrid_results.get(
                "exact_standards",
                []
            )
        )

        if standards:
            sections.append(
                "BIS STANDARD METADATA:\n"
                + standards
            )

    else:
        semantic = hybrid_results.get(
            "semantic",
            []
        )

        if semantic:
            semantic_lines = []

            for item in semantic[:5]:
                number = normalize_text(
                    item.get(
                        "standard_number"
                    ) or ""
                )

                title = normalize_text(
                    item.get(
                        "title"
                    ) or ""
                )

                text = normalize_text(
                    item.get(
                        "text"
                    ) or ""
                )

                text = text[:1800]

                parts = []

                if number:
                    parts.append(
                        f"Standard: {number}"
                    )

                if title:
                    parts.append(
                        f"Title: {title}"
                    )

                if text:
                    parts.append(
                        f"Content: {text}"
                    )

                if parts:
                    semantic_lines.append(
                        "\n".join(parts)
                    )

            if semantic_lines:
                sections.append(
                    "BIS SEMANTIC DATA:\n"
                    + "\n\n".join(
                        semantic_lines
                    )
                )

        standards = build_standard_context(
            hybrid_results.get(
                "exact_standards",
                []
            )
        )

        if standards:
            sections.append(
                "BIS STANDARD METADATA:\n"
                + standards
            )

        qco = build_qco_context(
            hybrid_results.get(
                "qco",
                []
            )
        )

        if qco:
            sections.append(
                "BIS QCO DATA:\n"
                + qco
            )

    if intent != "testing" and hybrid_results.get("tests"):
        sections.append(
            build_testing_context(
                hybrid_results.get("tests", []),
                query,
            )
        )

    if intent != "laboratory" and hybrid_results.get("labs"):
        sections.append(
            build_lab_context(hybrid_results.get("labs", []))
        )

    if intent != "qco" and hybrid_results.get("qco"):
        sections.append(
            build_qco_context(hybrid_results.get("qco", []))
        )

    core = hybrid_results.get("core", [])
    if core:
        core_lines = ["BIS CORE KNOWLEDGE:"]
        for item in core[:4]:
            title = normalize_text(item.get("title") or "")
            text = normalize_text(item.get("text") or "")
            source_url = item.get("source_url") or ""
            core_lines.append(
                " | ".join(
                    part for part in (
                        f"Topic: {title}" if title else "",
                        f"Information: {text}" if text else "",
                        f"Source: {source_url}" if source_url else "",
                    )
                    if part
                )
            )
        sections.append("\n".join(core_lines))

    return "\n\n".join(sections)


def _source_type(item):
    match_type = item.get("match_type", "")
    if match_type == "qco_relationship":
        return "qco"
    if match_type in {"lims_test", "lims_lab"}:
        return "lims"
    if match_type == "core_knowledge":
        return "core_bis_knowledge"
    if match_type == "firebase_semantic":
        return "semantic"
    return "standard"


def build_structured_sections(hybrid_results, query=""):
    sections = []
    standards = hybrid_results.get("exact_standards", [])
    tests = hybrid_results.get("tests", [])
    labs = hybrid_results.get("labs", [])
    qcos = hybrid_results.get("qco", [])
    core = hybrid_results.get("core", [])

    if standards:
        lines = []
        seen = set()
        for item in standards[:8]:
            number = normalize_text(item.get("standard_number") or "")
            title = normalize_text(item.get("title") or "")
            if not number and not title:
                continue
            key = (number, title)
            if key in seen:
                continue
            seen.add(key)
            details = [part for part in (
                f"**{number}**" if number else "",
                title,
                f"Published: {item.get('published_on')}" if item.get("published_on") else "",
                f"Department: {item.get('department')}" if item.get("department") else "",
                f"Sectional committee: {item.get('sectional_committee')}" if item.get("sectional_committee") else "",
            ) if part]
            lines.append(" - ".join(details))
        if lines:
            sections.append({
                "title": "Standard Overview",
                "content": "\n".join(f"- {line}" for line in lines),
                "evidence_type": "standard",
            })

    if tests:
        lines = []
        seen = set()
        for item in tests[:12]:
            key = (
                item.get("standard_number"),
                item.get("lab_code"),
                item.get("clause_raw"),
                item.get("designation"),
            )
            if key in seen:
                continue
            seen.add(key)
            details = [part for part in (
                f"Standard: {item.get('standard_number')}" if item.get("standard_number") else "",
                f"Product: {item.get('product')}" if item.get("product") else "",
                f"Clause/test scope: {item.get('clause_raw')}" if item.get("clause_raw") else "",
                f"Designation: {item.get('designation')}" if item.get("designation") else "",
                f"Test method: {item.get('test_method')}" if item.get("test_method") else "",
            ) if part]
            if details:
                lines.append(" - ".join(details))
        if lines:
            sections.append({
                "title": "Requirements / Testing",
                "content": "\n".join(f"- {line}" for line in lines),
                "evidence_type": "lims",
            })

    if labs:
        lines = []
        seen = set()
        for item in labs[:10]:
            key = (item.get("lab_code"), item.get("lab_name"))
            if key in seen:
                continue
            seen.add(key)
            details = [part for part in (
                f"**{item.get('lab_name')}**" if item.get("lab_name") else "",
                f"Lab code: {item.get('lab_code')}" if item.get("lab_code") else "",
                f"Standard: {item.get('standard_number')}" if item.get("standard_number") else "",
                f"Product/capability: {item.get('product')}" if item.get("product") else "",
                f"[View BIS LIMS record]({item.get('scope_url')})" if item.get("scope_url") else "",
            ) if part]
            if details:
                lines.append(" - ".join(details))
        if lines:
            sections.append({
                "title": "BIS Laboratories",
                "content": "\n".join(f"- {line}" for line in lines),
                "evidence_type": "lims",
            })

    if qcos:
        lines = []
        for item in qcos[:8]:
            details = [part for part in (
                f"Standard: {item.get('standard_number')}" if item.get("standard_number") else "",
                f"QCO: {item.get('qco_document_id')}" if item.get("qco_document_id") else "",
                f"Relationship: {item.get('relationship')}" if item.get("relationship") else "",
                f"Order: {item.get('order_number')}" if item.get("order_number") else "",
                f"Evidence: {normalize_text(item.get('evidence'))[:700]}" if item.get("evidence") else "",
            ) if part]
            if details:
                lines.append(" - ".join(details))
        if lines:
            sections.append({
                "title": "QCO / Mandatory Requirements",
                "content": "\n".join(f"- {line}" for line in lines),
                "evidence_type": "qco",
            })

    if core:
        lines = []
        for item in core[:4]:
            title = normalize_text(item.get("title") or "")
            text = normalize_text(item.get("text") or "")
            url = item.get("source_url")
            source = f" ([Official source]({url}))" if url else ""
            lines.append(f"- **{title}**: {text}{source}")
        if lines:
            sections.append({
                "title": "Certification / BIS Services",
                "content": "\n".join(lines),
                "evidence_type": "core_bis_knowledge",
            })

    return sections


def build_source_records(hybrid_results):
    records = []
    for category in ("exact_standards", "tests", "labs", "qco", "semantic", "core"):
        for item in hybrid_results.get(category, []):
            source_type = _source_type(item)
            source_url = item.get("document_url") or item.get("source_url") or item.get("scope_url")
            records.append({
                "type": source_type,
                "identifier": (
                    item.get("standard_number")
                    or item.get("qco_document_id")
                    or item.get("chunk_id")
                    or item.get("id")
                ),
                "title": item.get("title") or item.get("product") or item.get("document_type"),
                "source": item.get("source") or source_type,
                "url": source_url,
                "standard_number": item.get("standard_number"),
                "lab_name": item.get("lab_name"),
                "lab_code": item.get("lab_code"),
                "qco_identifier": item.get("qco_document_id"),
                "evidence": (
                    item.get("evidence")
                    or item.get("text")
                    or item.get("clause_raw")
                    or item.get("product")
                ),
                "match_type": item.get("match_type"),
                "distance": item.get("distance"),
            })

    unique = []
    seen = set()
    for record in records:
        key = (
            record.get("type"), record.get("identifier"),
            record.get("lab_code"), record.get("qco_identifier"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique[:40]


def build_followups(hybrid_results):
    if hybrid_results.get("is_numbers"):
        return [
            {"label": "View testing requirements", "query": f"What tests are required for {hybrid_results['is_numbers'][0]}?"},
            {"label": "Find BIS laboratories", "query": f"Which laboratories can test products according to {hybrid_results['is_numbers'][0]}?"},
            {"label": "Check related QCOs", "query": f"Does {hybrid_results['is_numbers'][0]} have a related QCO?"},
        ]
    return [
        {"label": "Find applicable standards", "query": "Which BIS standards are relevant to this product?"},
        {"label": "Find testing laboratories", "query": "Which BIS laboratories can test this product?"},
        {"label": "Check certification requirements", "query": "What BIS certification requirements apply?"},
    ]


def answer_matches_language(answer, language):
    if not answer:
        return False

    if language == "en":
        return True

    if language == "te":
        return bool(
            re.search(
                r'[\u0C00-\u0C7F]',
                answer
            )
        )

    if language == "hi":
        return bool(
            re.search(
                r'[\u0900-\u097F]',
                answer
            )
        )

    return True


def generate_answer(
    query,
    retrieved_results,
    language="en"
):
    if not client:
        return {
            "answer": (
                "The answer generation service "
                "is not configured."
            ),
            "sources": [],
            "sections": [],
            "evidence_status": "unavailable",
            "followups": build_followups(retrieved_results),
        }

    hybrid_results = retrieved_results

    context = build_context(
        hybrid_results,
        query
    )

    if not context:
        return {
            "answer": (
                "I could not find sufficient BIS "
                "information in the retrieved data "
                "to answer this question."
            ),
            "sources": build_source_records(hybrid_results),
            "sections": [],
            "evidence_status": "insufficient",
            "followups": build_followups(hybrid_results),
        }

    intent = hybrid_results.get(
        "intent"
    )

    system_prompt = """
You are StandIQ, an AI assistant for BIS Indian Standards and BIS services.

Answer ONLY from the supplied BIS retrieval context.

BIS Answering Rules:
1. Never invent BIS requirements, numerical limits, clauses, dates, fees, laboratories, QCO status, or test methods.
2. For testing questions, prioritize BIS LIMS TESTING DATA.
3. If the user asks about a specific clause, answer specifically from records belonging to that clause.
4. If the retrieved data gives test names or test methods but not permissible numerical limits, explicitly say that the numerical limits are not present in the retrieved data.
5. Do not claim that a QCO is mandatory unless the retrieved evidence explicitly supports that claim.
6. For laboratory questions, provide laboratory name and lab code when available.
7. For QCO questions, provide relationship and evidence when available.
8. Keep answers concise but complete.
9. Use official identifiers exactly as provided.
10. Do not reproduce raw database noise or duplicate records.
11. Do not treat laboratory testing charges as the chemical or physical limits of the standard.
12. If the retrieved data does not contain enough evidence to answer the question, clearly state that the retrieved BIS data is insufficient rather than guessing.
13. When answering clause-specific questions, do not substitute information from another clause merely because it concerns the same standard.
14. Distinguish clearly between:
   - requirements/limits stated in the standard,
   - tests available at BIS-recognized laboratories,
   - laboratory testing charges,
   - QCO relationships/evidence.
15. Prefer the most specific retrieved record over broad standard-level context.
16. When an exact IS identifier is present, prioritize the exact standard record and clearly separate it from related LIMS or QCO evidence.
17. For core BIS concepts, use only the supplied BIS CORE KNOWLEDGE and do not add unsupported legal or fee details.
"""

    user_prompt = f"""
USER QUERY:
{query}

INTENT:
{intent}

RETRIEVED BIS CONTEXT:
{context}

Answer the user's question using only the retrieved BIS context.
"""

    if language == "te":
        user_prompt += (
            "\nRespond in Telugu."
        )
    elif language == "hi":
        user_prompt += (
            "\nRespond in Hindi."
        )
    else:
        user_prompt += (
            "\nRespond in English."
        )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
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
            max_tokens=1400
        )

        raw_answer = response.choices[0].message.content

        print("RAW GROQ:", repr(raw_answer))

        answer = normalize_text(raw_answer)

        print("NORMALIZED:", repr(answer))

        answer = normalize_text(
            answer
        )

    except Exception as e:
        print(
            f"Generation error: "
            f"{type(e).__name__}: {e}"
        )

        return {
            "answer": (
                "I found relevant BIS data, "
                "but the answer could not be "
                "generated at this time."
            ),
            "sources": []
        }

    sources = []

    for item in hybrid_results.get(
        "exact_standards",
        []
    ):
        sources.append({
            "standard_number": item.get(
                "standard_number"
            ),
            "part": item.get("part"),
            "year": (
                item.get("year")
                or item.get("date")
            ),
            "title": item.get("title"),
            "source": item.get(
                "source",
                "BIS Standards Catalogue"
            ),
            "department": item.get(
                "department"
            ),
            "sectional_committee": item.get(
                "sectional_committee"
            ),
            "lab_name": None,
            "lab_code": None,
            "product": None,
            "clause": None,
            "testing_charge": None,
            "testing_charge_raw": None,
            "effective_date": None,
            "remark": None,
            "designation": None,
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "confidence": None,
            "evidence": None,
            "document_url": item.get(
                "document_url"
            ),
            "source_url": item.get(
                "source_url"
            ),
            "distance": item.get(
                "distance"
            )
        })

    for item in hybrid_results.get(
        "tests",
        []
    ):
        sources.append({
            "standard_number": (
                item.get(
                    "standard_number"
                )
                or item.get(
                    "indian_standard_no"
                )
            ),
            "part": None,
            "year": None,
            "title": item.get("title"),
            "source": item.get(
                "source",
                "BIS LIMS"
            ),
            "department": None,
            "sectional_committee": None,
            "lab_name": item.get(
                "lab_name"
            ),
            "lab_code": item.get(
                "lab_code"
            ),
            "product": item.get(
                "product"
            ),
            "clause": (
                item.get("clause")
                or item.get("clause_raw")
            ),
            "testing_charge": item.get(
                "testing_charge"
            ),
            "testing_charge_raw": item.get(
                "testing_charge_raw"
            ),
            "effective_date": item.get(
                "effective_date"
            ),
            "remark": item.get(
                "remark"
            ),
            "designation": item.get(
                "designation"
            ),
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "confidence": None,
            "evidence": None,
            "document_url": None,
            "source_url": (
                item.get("scope_url")
                or item.get("source")
            ),
            "distance": None
        })

    for item in hybrid_results.get(
        "labs",
        []
    ):
        sources.append({
            "standard_number": (
                item.get(
                    "standard_number"
                )
                or item.get(
                    "indian_standard_no"
                )
            ),
            "part": None,
            "year": None,
            "title": item.get("title"),
            "source": item.get(
                "source",
                "BIS LIMS"
            ),
            "department": None,
            "sectional_committee": None,
            "lab_name": item.get(
                "lab_name"
            ),
            "lab_code": item.get(
                "lab_code"
            ),
            "product": item.get(
                "product"
            ),
            "clause": item.get(
                "clause"
            ),
            "testing_charge": item.get(
                "testing_charge"
            ),
            "testing_charge_raw": item.get(
                "testing_charge_raw"
            ),
            "effective_date": item.get(
                "effective_date"
            ),
            "remark": item.get(
                "remark"
            ),
            "designation": item.get(
                "designation"
            ),
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "confidence": None,
            "evidence": None,
            "document_url": None,
            "source_url": (
                item.get("scope_url")
                or item.get("source")
            ),
            "distance": None
        })

    for item in hybrid_results.get(
        "qco",
        []
    ):
        sources.append({
            "standard_number": item.get(
                "standard_number"
            ),
            "part": None,
            "year": None,
            "title": None,
            "source": item.get(
                "source",
                "BIS QCO"
            ),
            "department": None,
            "sectional_committee": None,
            "lab_name": None,
            "lab_code": None,
            "product": None,
            "clause": None,
            "testing_charge": None,
            "testing_charge_raw": None,
            "effective_date": item.get(
                "order_date"
            ),
            "remark": None,
            "designation": None,
            "qco_document_id": item.get(
                "qco_document_id"
            ),
            "relationship": item.get(
                "relationship"
            ),
            "order_number": item.get(
                "order_number"
            ),
            "order_date": item.get(
                "order_date"
            ),
            "scheme": item.get(
                "scheme"
            ),
            "mandatory_qco": item.get(
                "mandatory_qco"
            ),
            "status": item.get(
                "status"
            ),
            "confidence": item.get(
                "confidence"
            ),
            "evidence": item.get(
                "evidence"
            ),
            "document_url": item.get(
                "document_url"
            ),
            "source_url": item.get(
                "source_url"
            ),
            "distance": None
        })

    for item in hybrid_results.get("semantic", []):
        sources.append({
            "standard_number": item.get("standard_number"),
            "part": None,
            "year": None,
            "title": item.get("title"),
            "source": item.get("source", "BIS Firestore Knowledge Base"),
            "department": None,
            "sectional_committee": None,
            "lab_name": None,
            "lab_code": None,
            "product": None,
            "clause": None,
            "testing_charge": None,
            "testing_charge_raw": None,
            "effective_date": None,
            "remark": None,
            "designation": None,
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "confidence": item.get("similarity"),
            "evidence": item.get("text"),
            "document_url": item.get("document_url"),
            "source_url": item.get("source_url"),
            "distance": item.get("distance"),
        })

    for item in hybrid_results.get("core", []):
        sources.append({
            "standard_number": None,
            "part": None,
            "year": None,
            "title": item.get("title"),
            "source": "BIS core knowledge",
            "department": None,
            "sectional_committee": None,
            "lab_name": None,
            "lab_code": None,
            "product": None,
            "clause": None,
            "testing_charge": None,
            "testing_charge_raw": None,
            "effective_date": None,
            "remark": None,
            "designation": None,
            "qco_document_id": None,
            "relationship": None,
            "order_number": None,
            "order_date": None,
            "scheme": None,
            "mandatory_qco": None,
            "status": None,
            "confidence": item.get("core_score"),
            "evidence": item.get("text"),
            "document_url": None,
            "source_url": item.get("source_url"),
            "distance": None,
        })

    structured_sources = build_source_records(hybrid_results)
    sections = build_structured_sections(hybrid_results, query)

    return {
        "answer": answer,
        "sources": structured_sources or sources,
        "sections": sections,
        "evidence_status": "supported" if structured_sources else "insufficient",
        "followups": build_followups(hybrid_results),
    }
