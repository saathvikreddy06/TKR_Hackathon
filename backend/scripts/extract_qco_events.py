import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QCO_DIR = ROOT / "data" / "normalized" / "qco"

DOCUMENTS_FILE = QCO_DIR / "qco_documents.json"
PAGES_FILE = QCO_DIR / "qco_pages.json"
OUTPUT_FILE = QCO_DIR / "qco_events.json"

ACTION_MAP = {
    "QCO": "ORIGINAL_QCO",
    "QCO_AMENDMENT": "AMENDMENT",
    "QCO_EXTENSION": "EXTENSION",
    "QCO_RESIND": "RESCIND",
    "QCO_EXEMPTION": "EXEMPTION",
    "QCO_DEFERMENT": "DEFERMENT",
    "QCO_CORRIGENDUM": "CORRIGENDUM",
}

IS_PATTERN = re.compile(
    r"\b(?:IS|IS/IEC|IEC)\s*[:./-]?\s*(\d{3,6})"
    r"(?:\s*[-/]\s*(\d{1,3}))?\b",
    re.I,
)

ORDER_PATTERN = re.compile(
    r"\b(?:S\.?\s*O\.?|G\.?\s*S\.?\s*R\.?)"
    r"\s*(?:NO\.?\s*)?[\w./() -]{1,80}",
    re.I,
)

DATE_PATTERNS = [
    re.compile(
        r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"
    ),
    re.compile(
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{4}\b",
        re.I,
    ),
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}\b",
        re.I,
    ),
]

ACTION_PATTERNS = {
    "AMENDMENT": [
        r"\bamend(?:s|ed|ment|ing)?\b",
        r"\bmodify\b",
        r"\bmodification\b",
    ],
    "EXTENSION": [
        r"\bextend(?:s|ed|ing)?\b",
        r"\bextension\b",
        r"\bextended\b",
    ],
    "RESCIND": [
        r"\brescind(?:s|ed|ing)?\b",
        r"\brescission\b",
        r"\bwithdraw(?:s|n|al)?\b",
        r"\brevoke(?:s|d)?\b",
    ],
    "EXEMPTION": [
        r"\bexempt(?:s|ed|ion)?\b",
        r"\bexemption\b",
    ],
    "DEFERMENT": [
        r"\bdefer(?:s|red|ment|ring)?\b",
        r"\bdeferment\b",
    ],
    "CORRIGENDUM": [
        r"\bcorrigendum\b",
        r"\bcorrection\b",
        r"\bcorrect(?:s|ed|ion)?\b",
    ],
}


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def extract_is(text):
    values = []

    for match in IS_PATTERN.finditer(text or ""):
        number = match.group(1)
        part = match.group(2)

        values.append(
            f"{number}-{part}" if part else number
        )

    return sorted(set(values))


def extract_orders(text):
    return sorted({
        clean(match.group(0))
        for match in ORDER_PATTERN.finditer(text or "")
    })


def extract_dates(text):
    dates = []

    for pattern in DATE_PATTERNS:
        dates.extend(
            match.group(0)
            for match in pattern.finditer(text or "")
        )

    return sorted(set(dates))


def build_page_text(pages):
    grouped = defaultdict(list)

    for page in pages:
        document_id = page.get("document_id")

        if document_id:
            grouped[document_id].append({
                "page": page.get("page_number"),
                "text": page.get("text", ""),
            })

    return dict(grouped)


def detect_actions(document_type, text):
    if document_type in ACTION_MAP:
        mapped = ACTION_MAP[document_type]

        if mapped != "ORIGINAL_QCO":
            return [mapped]

        return ["ORIGINAL_QCO"]

    detected = []

    text_lower = text.lower()

    for action, patterns in ACTION_PATTERNS.items():
        if any(
            re.search(pattern, text_lower)
            for pattern in patterns
        ):
            detected.append(action)

    return detected or ["UNKNOWN"]


def evidence_for_action(text, action):
    patterns = ACTION_PATTERNS.get(action, [])

    if not patterns:
        return None

    text = text or ""

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.I,
        )

        if not match:
            continue

        start = max(0, match.start() - 350)
        end = min(len(text), match.end() + 650)

        return clean(text[start:end])

    return None


def classify_confidence(
    document,
    action,
    is_numbers,
    orders,
    evidence,
):
    score = 0

    document_type = document.get("document_type")

    if document_type in ACTION_MAP:
        score += 50

    if is_numbers:
        score += 25

    if orders:
        score += 15

    if evidence:
        score += 20

    if action == "UNKNOWN":
        return "LOW"

    if score >= 80:
        return "HIGH"

    if score >= 50:
        return "MEDIUM"

    return "LOW"


def extract_event(document, page_rows):
    document_id = document["document_id"]

    full_text = "\n".join(
        row.get("text", "")
        for row in page_rows
    )

    full_text = clean(full_text)

    combined_text = " ".join([
        document.get("title", ""),
        Path(document.get("raw_file", "")).stem,
        full_text,
    ])

    is_numbers = sorted(
        set(document.get("is_numbers") or [])
        | set(extract_is(combined_text))
    )

    orders = sorted(
        set(document.get("order_numbers") or [])
        | set(extract_orders(combined_text))
    )

    dates = sorted(
        set(document.get("dates_found") or [])
        | set(extract_dates(combined_text))
    )

    actions = detect_actions(
        document.get("document_type"),
        combined_text,
    )

    events = []

    for action in actions:
        evidence = evidence_for_action(
            full_text,
            action,
        )

        confidence = classify_confidence(
            document,
            action,
            is_numbers,
            orders,
            evidence,
        )

        events.append({
            "event_id": (
                f"{document_id}_{action.lower()}"
            ),
            "document_id": document_id,
            "event_type": action,
            "document_type": document.get(
                "document_type"
            ),
            "title": document.get("title"),
            "is_numbers": is_numbers,
            "order_numbers": orders,
            "dates_found": dates,
            "source_url": document.get("source_url"),
            "final_url": document.get("final_url"),
            "raw_file": document.get("raw_file"),
            "sha256": document.get("sha256"),
            "page_count": document.get("page_count"),
            "evidence": evidence,
            "confidence": confidence,
        })

    return events


def main():
    documents = json.loads(
        DOCUMENTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    pages = json.loads(
        PAGES_FILE.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(pages, dict):
        pages = pages.get("pages", [])

    page_map = build_page_text(pages)

    events = []
    failures = []

    for index, document in enumerate(
        documents,
        start=1,
    ):
        try:
            document_events = extract_event(
                document,
                page_map.get(
                    document["document_id"],
                    [],
                ),
            )

            events.extend(document_events)

        except Exception as exc:
            failures.append({
                "document_id": document.get(
                    "document_id"
                ),
                "error": str(exc),
            })

        if index % 50 == 0:
            print(
                f"Processed {index}/{len(documents)}"
            )

    metadata = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "documents": len(documents),
        "events": len(events),
        "failures": len(failures),
        "method": (
            "document type + explicit action "
            "patterns + IS/order/date extraction"
        ),
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "events": events,
                "failures": failures,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("BIS QCO EVENT EXTRACTION")
    print(f"Documents:     {len(documents)}")
    print(f"Events:        {len(events)}")
    print(f"Failures:      {len(failures)}")

    from collections import Counter

    counts = Counter(
        event["event_type"]
        for event in events
    )

    print()
    print("EVENT TYPES")

    for event_type, count in counts.most_common():
        print(
            f"  {event_type:<20} {count}"
        )

    confidence = Counter(
        event["confidence"]
        for event in events
    )

    print()
    print("CONFIDENCE")

    for level, count in confidence.most_common():
        print(
            f"  {level:<20} {count}"
        )

    print()
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()