import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QCO_DIR = ROOT / "data" / "normalized" / "qco"

DOCUMENTS_FILE = QCO_DIR / "qco_documents.json"
PAGES_FILE = QCO_DIR / "qco_pages.json"
LINEAGE_FILE = QCO_DIR / "qco_lineage.json"
STATE_FILE = QCO_DIR / "qco_current_state.json"

FOLLOW_UP_TYPES = {
    "QCO_AMENDMENT": "AMENDS",
    "QCO_EXTENSION": "EXTENDS",
    "QCO_RESIND": "RESCINDS",
    "QCO_EXEMPTION": "EXEMPTS",
    "QCO_DEFERMENT": "DEFERS",
    "QCO_CORRIGENDUM": "CORRECTS",
}

IS_PATTERN = re.compile(
    r"\b(?:IS|IS/IEC|IEC)\s*[:./-]?\s*(\d{3,6})"
    r"(?:\s*[-/]\s*(\d{1,3}))?\b",
    re.I,
)

ORDER_PATTERN = re.compile(
    r"\b(?:S\.?\s*O\.?|G\.?\s*S\.?\s*R\.?)\s*"
    r"(?:NO\.?\s*)?[\w./() -]{1,80}",
    re.I,
)

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def normalize_is(values):
    result = []

    for value in values:
        value = re.sub(r"\s+", "", value)
        if re.fullmatch(r"\d{3,6}(?:-\d{1,3})?", value):
            result.append(value)

    return sorted(set(result))

def extract_is(text):
    values = []

    for match in IS_PATTERN.finditer(text or ""):
        number = match.group(1)
        part = match.group(2)

        values.append(
            f"{number}-{part}" if part else number
        )

    return normalize_is(values)

def build_page_text(pages):
    grouped = defaultdict(list)

    for page in pages:
        document_id = page.get("document_id")
        if document_id:
            grouped[document_id].append(page.get("text", ""))

    return {
        document_id: "\n".join(values)
        for document_id, values in grouped.items()
    }

def normalized_title(document):
    title = document.get("title") or ""
    filename = Path(document.get("raw_file") or "").stem

    value = f"{title} {filename}".lower()
    value = value.replace("_", " ")
    value = re.sub(r"[-]+", " ", value)
    value = re.sub(r"\b\d{3,6}\b", " ", value)
    value = re.sub(r"\b(19|20)\d{2}\b", " ", value)

    return clean(value)

def product_tokens(document):
    value = normalized_title(document)

    stop = {
        "quality",
        "control",
        "order",
        "amendment",
        "extension",
        "rescind",
        "rescindment",
        "exemption",
        "deferment",
        "corrigendum",
        "notification",
        "gazette",
        "indian",
        "standard",
        "standards",
        "government",
        "central",
        "ministry",
        "bureau",
        "following",
        "namely",
        "order",
        "second",
        "third",
        "fourth",
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
        "2026",
    }

    return {
        token
        for token in re.findall(r"[a-z]{4,}", value)
        if token not in stop
    }

def explicit_title_reference(source, target, source_text):
    target_title = clean(target.get("title", ""))
    source_lower = clean(source_text).lower()

    if not target_title or len(target_title) < 15:
        return False

    target_lower = target_title.lower()

    if target_lower in source_lower:
        return True

    target_lower = re.sub(
        r"[_\-]+",
        " ",
        target_lower,
    )

    target_lower = re.sub(
        r"\s+",
        " ",
        target_lower,
    ).strip()

    if target_lower in source_lower:
        return True

    return False

def order_references(text):
    return {
        clean(match.group(0)).lower()
        for match in ORDER_PATTERN.finditer(text or "")
    }

def find_relationships(document, documents, page_text):
    source_type = document.get("document_type")

    if source_type not in FOLLOW_UP_TYPES:
        return []

    source_id = document["document_id"]
    source_text = page_text.get(source_id, "")

    source_is = set(
        document.get("is_numbers") or []
    )

    if not source_is:
        source_is = set(
            extract_is(
                " ".join([
                    document.get("title", ""),
                    Path(document.get("raw_file", "")).stem,
                    source_text,
                ])
            )
        )

    candidates = []

    for target in documents:
        target_id = target["document_id"]

        if target_id == source_id:
            continue

        if target.get("document_type") not in {
            "QCO",
            "QCO_AMENDMENT",
            "QCO_EXTENSION",
            "QCO_EXEMPTION",
            "QCO_DEFERMENT",
            "QCO_RESIND",
            "QCO_CORRIGENDUM",
        }:
            continue

        target_is = set(
            target.get("is_numbers") or []
        )

        is_overlap = source_is & target_is

        explicit_reference = explicit_title_reference(
            document,
            target,
            source_text,
        )

        if not is_overlap and not explicit_reference:
            continue

        evidence = []

        if is_overlap:
            evidence.append({
                "type": "IS_OVERLAP",
                "values": sorted(is_overlap),
            })

        if explicit_reference:
            evidence.append({
                "type": "EXPLICIT_TARGET_REFERENCE",
            })

        if is_overlap and explicit_reference:
            confidence = "HIGH"
            score = 100
        elif is_overlap:
            confidence = "HIGH"
            score = 90
        else:
            confidence = "MEDIUM"
            score = 70

        candidates.append({
            "source_document_id": source_id,
            "source_document_type": source_type,
            "target_document_id": target_id,
            "target_document_type": target.get(
                "document_type"
            ),
            "relationship_type": FOLLOW_UP_TYPES[
                source_type
            ],
            "confidence": confidence,
            "score": score,
            "evidence": evidence,
        })

    return candidates

def build_state(documents, lineage):
    by_is = defaultdict(list)

    for document in documents:
        for is_number in document.get("is_numbers") or []:
            by_is[is_number].append(document["document_id"])

    relationships_by_target = defaultdict(list)

    for relation in lineage:
        relationships_by_target[
            relation["target_document_id"]
        ].append(relation)

    states = []

    for is_number, document_ids in sorted(by_is.items()):
        related = [
            next(
                d for d in documents
                if d["document_id"] == document_id
            )
            for document_id in document_ids
        ]

        def ids(document_type):
            return [
                d["document_id"]
                for d in related
                if d.get("document_type") == document_type
            ]

        rescinds = ids("QCO_RESIND")

        if rescinds:
            status = "REQUIRES_CURRENT_STATUS_REVIEW"
        elif ids("QCO"):
            status = "QCO_IDENTIFIED"
        else:
            status = "REGULATORY_REFERENCE"

        states.append({
            "is_number": is_number,
            "status": status,
            "base_qco_documents": ids("QCO"),
            "amendment_documents": ids("QCO_AMENDMENT"),
            "extension_documents": ids("QCO_EXTENSION"),
            "rescind_documents": rescinds,
            "exemption_documents": ids("QCO_EXEMPTION"),
            "deferment_documents": ids("QCO_DEFERMENT"),
            "corrigendum_documents": ids("QCO_CORRIGENDUM"),
            "document_count": len(related),
        })

    return states

def main():
    documents = json.loads(
        DOCUMENTS_FILE.read_text(encoding="utf-8")
    )

    pages = json.loads(
        PAGES_FILE.read_text(encoding="utf-8")
    )

    if isinstance(pages, dict):
        pages = pages.get("pages", [])

    page_text = build_page_text(pages)

    lineage = []

    for index, document in enumerate(documents, 1):
        lineage.extend(
            find_relationships(
                document,
                documents,
                page_text,
            )
        )

        if index % 50 == 0:
            print(
                f"Analyzed {index}/{len(documents)} documents"
            )

    states = build_state(
        documents,
        lineage,
    )

    metadata = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "documents": len(documents),
        "lineage_relationships": len(lineage),
        "is_states": len(states),
        "method": (
            "strict evidence: IS overlap, "
            "explicit document reference, "
            "order reference overlap"
        ),
    }

    LINEAGE_FILE.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "relationships": lineage,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    STATE_FILE.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "states": states,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("BIS QCO LINEAGE")
    print(f"Documents:             {len(documents)}")
    print(f"Relationships:         {len(lineage)}")
    print(f"IS states:             {len(states)}")
    print(
        f"High confidence:       "
        f"{sum(r['confidence'] == 'HIGH' for r in lineage)}"
    )
    print(
        f"Medium confidence:     "
        f"{sum(r['confidence'] == 'MEDIUM' for r in lineage)}"
    )
    print()
    print(f"Lineage: {LINEAGE_FILE}")
    print(f"State:   {STATE_FILE}")

if __name__ == "__main__":
    main()