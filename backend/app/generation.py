import json
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

    for item in standards[:5]:
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
                f"Description: {description[:500]}"
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

    for item in qcos[:5]:
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

    if intent != "testing":
        testing = build_testing_context(
            hybrid_results.get("tests", []),
            query,
        )
        if testing:
            sections.append(testing)

    if intent != "laboratory":
        labs = build_lab_context(hybrid_results.get("labs", []))
        if labs:
            sections.append(labs)

    if intent != "qco":
        qco = build_qco_context(hybrid_results.get("qco", []))
        if qco:
            sections.append("BIS QCO DATA:\n" + qco)

    return "\n\n".join(sections)


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


def _flatten_retrieved_sources(hybrid_results):
    sources = []

    for group_name in ("exact_standards", "semantic", "tests", "labs", "qco"):
        for item in hybrid_results.get(group_name, []):
            if group_name == "semantic":
                metadata = item.get("metadata") or {}
                source = {
                    "id": item.get("chunk_id") or item.get("document_id") or item.get("standard_number") or "semantic-source",
                    "type": "standard",
                    "identifier": item.get("standard_number") or metadata.get("standard_number") or metadata.get("is_number") or metadata.get("indian_standard_no") or "BIS record",
                    "title": item.get("title") or metadata.get("title") or metadata.get("standard_name") or "BIS record",
                    "source": item.get("source") or metadata.get("source") or "BIS Firestore Knowledge Base",
                    "url": item.get("source_url") or metadata.get("source_url") or metadata.get("document_url"),
                    "evidence": item.get("text") or metadata.get("text") or metadata.get("description") or "Retrieved BIS evidence.",
                    "standard_number": item.get("standard_number") or metadata.get("standard_number") or metadata.get("is_number") or metadata.get("indian_standard_no"),
                    "document_url": item.get("document_url") or metadata.get("document_url"),
                    "source_url": item.get("source_url") or metadata.get("source_url"),
                    "lab_name": None,
                    "lab_code": None,
                    "qco_document_id": None,
                    "relationship": None,
                    "part": item.get("part") or metadata.get("part"),
                    "year": item.get("published_on") or metadata.get("published_on") or metadata.get("year"),
                    "match_type": item.get("match_type") or "firebase_semantic",
                }
            elif group_name == "tests":
                source = {
                    "id": item.get("id") or item.get("standard_number") or item.get("lab_code") or "test-source",
                    "type": "testing",
                    "identifier": item.get("standard_number") or item.get("indian_standard_no") or "BIS test record",
                    "title": item.get("title") or item.get("product") or "BIS test record",
                    "source": item.get("source") or "BIS LIMS",
                    "url": item.get("source_url") or item.get("scope_url"),
                    "evidence": item.get("testing_charge_raw") or item.get("description") or item.get("test_method") or item.get("remark") or "Testing evidence from BIS LIMS.",
                    "standard_number": item.get("standard_number") or item.get("indian_standard_no"),
                    "lab_name": item.get("lab_name"),
                    "lab_code": item.get("lab_code"),
                    "qco_document_id": None,
                    "relationship": None,
                    "part": None,
                    "year": None,
                    "match_type": item.get("match_type") or "lims_test",
                }
            elif group_name == "labs":
                source = {
                    "id": item.get("lab_code") or item.get("lab_name") or item.get("standard_number") or "lab-source",
                    "type": "laboratory",
                    "identifier": item.get("lab_code") or item.get("lab_name") or "BIS laboratory",
                    "title": item.get("lab_name") or "BIS laboratory",
                    "source": item.get("source") or "BIS LIMS",
                    "url": item.get("source_url") or item.get("scope_url"),
                    "evidence": item.get("product") or item.get("designation") or item.get("remark") or "Laboratory information from BIS records.",
                    "standard_number": item.get("standard_number") or item.get("indian_standard_no"),
                    "lab_name": item.get("lab_name"),
                    "lab_code": item.get("lab_code"),
                    "qco_document_id": None,
                    "relationship": None,
                    "part": None,
                    "year": None,
                    "match_type": item.get("match_type") or "lims_lab",
                }
            elif group_name == "qco":
                source = {
                    "id": item.get("qco_document_id") or item.get("order_number") or item.get("standard_number") or "qco-source",
                    "type": "qco",
                    "identifier": item.get("qco_document_id") or item.get("relationship") or item.get("order_number") or "QCO relationship",
                    "title": item.get("relationship") or "QCO relationship",
                    "source": item.get("source") or "BIS QCO",
                    "url": item.get("source_url") or item.get("document_url"),
                    "evidence": item.get("evidence") or item.get("relationship") or "QCO relationship evidence from retrieved BIS records.",
                    "standard_number": item.get("standard_number"),
                    "lab_name": None,
                    "lab_code": None,
                    "qco_document_id": item.get("qco_document_id"),
                    "relationship": item.get("relationship"),
                    "part": None,
                    "year": item.get("order_date"),
                    "match_type": item.get("match_type") or "qco_relationship",
                }
            else:
                source = {
                    "id": item.get("document_id") or item.get("standard_number") or "standard-source",
                    "type": "standard",
                    "identifier": item.get("standard_number") or "BIS standard",
                    "title": item.get("title") or "BIS standard",
                    "source": item.get("source") or "BIS Standards Catalogue",
                    "url": item.get("source_url") or item.get("document_url"),
                    "evidence": item.get("evidence") or item.get("description") or "Retrieved BIS standard detail.",
                    "standard_number": item.get("standard_number"),
                    "document_url": item.get("document_url"),
                    "source_url": item.get("source_url"),
                    "lab_name": None,
                    "lab_code": None,
                    "qco_document_id": None,
                    "relationship": None,
                    "part": item.get("part"),
                    "year": item.get("year") or item.get("published_on") or item.get("date"),
                    "match_type": item.get("match_type") or "exact_standard",
                }

            sources.append(source)

    return sources


def _collect_standard_references(hybrid_results):
    items = []
    seen = set()

    for group_name in ("exact_standards", "semantic"):
        for item in hybrid_results.get(group_name, []):
            if group_name == "semantic":
                metadata = item.get("metadata") or {}
                standard_number = item.get("standard_number") or metadata.get("standard_number") or metadata.get("is_number") or metadata.get("indian_standard_no")
                title = item.get("title") or metadata.get("title") or metadata.get("standard_name") or "BIS standard"
                description = item.get("text") or metadata.get("description") or metadata.get("summary") or "Retrieved BIS evidence."
            else:
                standard_number = item.get("standard_number") or item.get("is_number") or item.get("number")
                title = item.get("title") or item.get("name") or "BIS standard"
                description = item.get("description") or item.get("summary") or "Retrieved BIS standard information."

            if not standard_number:
                continue

            key = str(standard_number).strip().lower()
            if key in seen:
                continue
            seen.add(key)

            items.append({
                "standard_number": standard_number,
                "title": title,
                "description": description[:500],
                "evidence_id": item.get("chunk_id") or item.get("document_id") or item.get("qco_document_id") or str(standard_number),
            })

    return items[:8]


def _collect_lab_records(hybrid_results):
    labs = []
    for item in hybrid_results.get("labs", []):
        lab_code = item.get("lab_code") or "-"
        lab_name = item.get("lab_name") or "BIS laboratory"
        labs.append({
            "lab_name": lab_name,
            "lab_code": lab_code,
            "capability": item.get("product") or item.get("designation") or item.get("remark") or "Laboratory information available in retrieved BIS records.",
            "standard_number": item.get("standard_number") or item.get("indian_standard_no") or "-",
        })
    return labs[:8]


def _collect_test_records(hybrid_results):
    tests = []
    for item in hybrid_results.get("tests", []):
        tests.append({
            "standard_number": item.get("standard_number") or item.get("indian_standard_no") or "-",
            "product": item.get("product") or "-",
            "designation": item.get("designation") or "-",
            "lab_name": item.get("lab_name") or "-",
            "lab_code": item.get("lab_code") or "-",
            "evidence": item.get("testing_charge_raw") or item.get("description") or item.get("test_method") or item.get("remark") or "Test evidence available in retrieved BIS records.",
        })
    return tests[:8]


def _collect_qco_records(hybrid_results):
    qcos = []
    for item in hybrid_results.get("qco", []):
        qcos.append({
            "qco_document_id": item.get("qco_document_id") or "-",
            "relationship": item.get("relationship") or "Retrieved QCO relationship",
            "evidence": item.get("evidence") or "Retrieved BIS QCO evidence.",
            "standard_number": item.get("standard_number") or "-",
        })
    return qcos[:8]


def _build_structured_sections(query, hybrid_results):
    sections = []
    standards = _collect_standard_references(hybrid_results)
    tests = _collect_test_records(hybrid_results)
    labs = _collect_lab_records(hybrid_results)
    qcos = _collect_qco_records(hybrid_results)

    if standards:
        sections.append({
            "type": "standards",
            "title": "Relevant Standards",
            "items": standards,
        })

    if tests:
        sections.append({
            "type": "testing",
            "title": "Testing & Requirements",
            "content": "The retrieved BIS records include test-related evidence for the identified standard(s). Details are presented below without inferring any unsupported numerical limits.",
            "tests": tests,
        })
    else:
        sections.append({
            "type": "testing",
            "title": "Testing & Requirements",
            "content": "Testing information was not available in the retrieved BIS records.",
            "tests": [],
        })

    if labs:
        sections.append({
            "type": "laboratories",
            "title": "BIS Laboratories",
            "content": "Relevant laboratory information retrieved from BIS records.",
            "labs": labs,
        })
    elif hybrid_results.get("structured_status") == "error":
        sections.append({
            "type": "laboratories",
            "title": "BIS Laboratories",
            "content": (
                "Laboratory retrieval was unavailable because the BIS LIMS "
                f"data source could not be read: {hybrid_results.get('structured_error')}."
            ),
            "labs": [],
        })
    else:
        sections.append({
            "type": "laboratories",
            "title": "BIS Laboratories",
            "content": (
                "No verified laboratory relationship was found in the retrieved "
                "BIS LIMS data for the relevant standards/tests."
            ),
            "labs": [],
        })

    if qcos:
        sections.append({
            "type": "qco",
            "title": "QCO / Mandatory Requirements",
            "content": "The retrieved BIS evidence includes a QCO relationship. The relationship is described exactly as retrieved and is not inferred beyond the supporting record.",
            "qcos": qcos,
        })
    elif hybrid_results.get("qco_status") == "error":
        sections.append({
            "type": "qco",
            "title": "QCO / Mandatory Requirements",
            "content": (
                "QCO retrieval was unavailable because the QCO data source "
                f"could not be read: {hybrid_results.get('qco_error')}."
            ),
            "qcos": [],
        })
    else:
        sections.append({
            "type": "qco",
            "title": "QCO / Mandatory Requirements",
            "content": (
                "No verified QCO relationship was found in the retrieved data "
                "for the relevant standards."
            ),
            "qcos": [],
        })

    sections.append({
        "type": "certification",
        "title": "Certification / Conformity Assessment",
        "content": "Certification information was not available in the retrieved evidence.",
    })

    if standards:
        sections.append({
            "type": "related",
            "title": "Related Standards",
            "content": "Related BIS records were retrieved for the queried product or standard area and are listed above where supported by evidence.",
            "items": standards,
        })

    return sections


def _build_followups(query, hybrid_results):
    followups = []
    query_lower = (query or "").lower()

    if "laboratory" in query_lower or "labs" in query_lower or "test" in query_lower:
        followups.append({"label": "Find BIS Laboratories", "query": "Which BIS laboratories can test this standard?"})
    if "qco" in query_lower or "mandatory" in query_lower or "related" in query_lower:
        followups.append({"label": "Check Related QCOs", "query": "Does this standard have a related QCO?"})
    if hybrid_results.get("exact_standards") or hybrid_results.get("semantic"):
        followups.append({"label": "Show Related Standards", "query": "Show related BIS standards for this product or material."})
    if not followups:
        followups.append({"label": "Show Testing Requirements", "query": "What tests are required under this BIS standard?"})
    return followups[:4]


def _extract_json_object(raw_text):
    if not raw_text:
        return None

    text = str(raw_text).strip()
    if not text:
        return None

    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL)

    start = text.find("{")
    if start == -1:
        return None

    for idx in range(start, len(text)):
        if text[idx] != "{":
            continue

        depth = 0
        in_string = False
        escaped = False

        for jdx in range(idx, len(text)):
            ch = text[jdx]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[idx:jdx + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
                        return None

    end = text.rfind("}")
    if end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def _render_structured_markdown(title, summary, sections, sources):
    lines = [f"# {title}", "", f"{summary}", ""]

    for section in sections:
        lines.append(f"## {section.get('title', 'Details')}")
        content = section.get("content")
        if content:
            lines.append(content)
            lines.append("")

        items = section.get("items") or []
        if items:
            for item in items:
                number = item.get("standard_number") or "BIS record"
                title_text = item.get("title") or "Supporting BIS record"
                description = item.get("description") or ""
                lines.append(f"### {number}")
                lines.append(f"**Title:** {title_text}")
                if description:
                    lines.append(f"**Description:** {description}")
                lines.append("")

        tests = section.get("tests") or []
        if tests:
            for test in tests:
                lines.append(f"- **Standard:** {test.get('standard_number') or '-'}")
                lines.append(f"  **Product:** {test.get('product') or '-'}")
                lines.append(f"  **Evidence:** {test.get('evidence') or 'Not available in retrieved records.'}")
                lines.append("")

        labs = section.get("labs") or []
        if labs:
            lines.append("| Laboratory | Lab Code | Relevant Capability |")
            lines.append("|---|---|---|")
            for lab in labs:
                lines.append(f"| {lab.get('lab_name') or '-'} | {lab.get('lab_code') or '-'} | {lab.get('capability') or '-'} |")
            lines.append("")

        qcos = section.get("qcos") or []
        if qcos:
            for qco in qcos:
                lines.append(f"- **QCO identifier:** {qco.get('qco_document_id') or '-'}")
                lines.append(f"  **Relationship:** {qco.get('relationship') or 'No relationship text retrieved.'}")
                lines.append(f"  **Evidence:** {qco.get('evidence') or 'No evidence retrieved.'}")
                lines.append("")

    if sources:
        lines.append("## Sources & Evidence")
        for index, source in enumerate(sources[:8], 1):
            identifier = source.get("identifier") or source.get("standard_number") or source.get("qco_document_id") or source.get("lab_code") or "BIS record"
            title_text = source.get("title") or source.get("source") or "Source"
            evidence = source.get("evidence") or "Evidence text was not provided in the retrieved metadata."
            url = source.get("url") or source.get("source_url") or source.get("document_url")
            lines.append(f"### Source {index} — {source.get('type', 'source').title()}")
            lines.append(f"**{identifier}**")
            lines.append(f"{title_text}")
            lines.append(f"**Source:** {source.get('source') or 'BIS record'}")
            lines.append(f"**Evidence:** {evidence}")
            if url:
                lines.append(f"[View official source →]({url})")
            lines.append("")

    return "\n".join(lines).strip()


def generate_answer(
    query,
    retrieved_results,
    language="en"
):
    hybrid_results = retrieved_results

    if not client:
        structured = {
            "title": "BIS Information",
            "summary": "The answer generation service is not configured.",
            "sections": _build_structured_sections(query, hybrid_results),
            "sources": _flatten_retrieved_sources(hybrid_results),
            "followups": _build_followups(query, hybrid_results),
            "evidence_status": "insufficient" if not _flatten_retrieved_sources(hybrid_results) else "supported",
        }
        return {
            "answer": _render_structured_markdown(
                structured["title"],
                structured["summary"],
                structured["sections"],
                structured["sources"],
            ),
            **structured,
        }

    context = build_context(
        hybrid_results,
        query
    )

    if not context:
        structured = {
            "title": "BIS Information",
            "summary": "I could not find sufficient BIS information in the retrieved data to answer this question.",
            "sections": [{
                "type": "overview",
                "title": "Overview",
                "content": "The retrieved BIS data was insufficient to answer this question without making unsupported claims.",
            }],
            "sources": [],
            "followups": _build_followups(query, hybrid_results),
            "evidence_status": "insufficient",
        }
        return {
            "answer": _render_structured_markdown(
                structured["title"],
                structured["summary"],
                structured["sections"],
                structured["sources"],
            ),
            **structured,
        }

    structured_payload = {
        "title": "BIS Information",
        "summary": "Based on the available BIS records.",
        "sections": _build_structured_sections(query, hybrid_results),
        "sources": _flatten_retrieved_sources(hybrid_results),
        "followups": _build_followups(query, hybrid_results),
        "evidence_status": "supported" if _flatten_retrieved_sources(hybrid_results) else "insufficient",
    }

    intent = hybrid_results.get("intent")
    system_prompt = """
You are StandIQ, an AI assistant for BIS Indian Standards and BIS services.

Return valid JSON only, with no Markdown fences, no commentary, and no extra text.
Use the supplied BIS retrieval context only.

Required JSON shape:
{
  "title": "string",
  "summary": "string",
  "sections": [
    {"type": "overview|standards|testing|laboratories|qco|certification|related", "title": "string", "content": "string", "items": [{"standard_number":"string","title":"string","description":"string","evidence_id":"string"}], "tests": [{"standard_number":"string","product":"string","designation":"string","lab_name":"string","lab_code":"string","evidence":"string"}], "labs": [{"lab_name":"string","lab_code":"string","capability":"string","standard_number":"string"}], "qcos": [{"qco_document_id":"string","relationship":"string","evidence":"string","standard_number":"string"}] }
  ],
  "followups": [{"label": "string", "query": "string"}]
}

Rules:
1. Never invent BIS requirements, numerical limits, clauses, dates, fees, laboratories, QCO status, or test methods.
2. Do not claim a standard is mandatory unless the retrieved record explicitly supports it.
3. If evidence is missing, say so clearly instead of guessing.
4. Reference only evidence_ids that are actually supplied in the retrieval context.
5. For QCO sections, show only actual retrieved QCO relationships.
6. Keep it concise but structured.
7. Use official identifiers exactly as provided.
8. The response must be in the language requested by the user.
"""

    user_prompt = f"""
USER QUERY:
{query}

INTENT:
{intent}

RETRIEVED BIS CONTEXT:
{context}

The following evidence IDs are valid and must be referenced only as needed:
{[item.get('id') or item.get('qco_document_id') or item.get('standard_number') or item.get('lab_code') for item in _flatten_retrieved_sources(hybrid_results)]}

Return only valid JSON.
"""

    if language == "te":
        user_prompt += "\nRespond in Telugu."
    elif language == "hi":
        user_prompt += "\nRespond in Hindi."
    else:
        user_prompt += "\nRespond in English."

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1800,
        )

        raw_response = response.choices[0].message.content
        if raw_response:
            parsed = _extract_json_object(raw_response)
            if isinstance(parsed, dict):
                structured_payload = {
                    "title": parsed.get("title") or structured_payload["title"],
                    "summary": parsed.get("summary") or structured_payload["summary"],
                    "sections": structured_payload["sections"],
                    "followups": parsed.get("followups") or structured_payload["followups"],
                    "sources": _flatten_retrieved_sources(hybrid_results),
                    "evidence_status": "supported" if _flatten_retrieved_sources(hybrid_results) else "insufficient",
                }
    except Exception as exc:
        print(f"Structured generation error: {type(exc).__name__}: {exc}")

    answer_text = _render_structured_markdown(
        structured_payload["title"],
        structured_payload["summary"],
        structured_payload["sections"],
        structured_payload["sources"],
    )

    return {
        "answer": answer_text,
        "title": structured_payload["title"],
        "summary": structured_payload["summary"],
        "sections": structured_payload["sections"],
        "sources": structured_payload["sources"],
        "followups": structured_payload.get("followups", []),
        "evidence_status": structured_payload["evidence_status"],
        "confidence": "High" if structured_payload["sources"] else "Insufficient evidence",
    }
