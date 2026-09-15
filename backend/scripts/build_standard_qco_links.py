import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

STANDARDS_FILE = (
    DATA / "normalized" / "standards"
    / "bis_standards.json"
)

EVENTS_FILE = (
    DATA / "normalized" / "qco"
    / "qco_events.json"
)

OUTPUT_FILE = (
    DATA / "normalized" / "standards"
    / "standard_qco_links.json"
)

AUDIT_FILE = (
    DATA / "manifests"
    / "standard_qco_links_manifest.json"
)


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_name(
        f"{path.name}.{datetime.now().timestamp()}.tmp"
    )

    tmp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for _ in range(5):
        try:
            if path.exists():
                path.unlink()
            tmp.rename(path)
            return
        except PermissionError:
            import time
            time.sleep(1)

    raise PermissionError(f"Could not replace {path}")


def normalize(value):
    value = str(value or "").upper()
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_is(value):
    text = normalize(value)

    matches = re.findall(
        r"\bIS\s*[-:]?\s*(\d{1,6})",
        text,
    )

    return {
        f"IS {number}"
        for number in matches
    }


def standard_numbers(standard):
    numbers = set()

    numbers |= extract_is(
        standard.get("standard_number")
    )

    for reference in standard.get(
        "lims_references",
        [],
    ):
        if isinstance(reference, dict):
            reference = json.dumps(
                reference,
                ensure_ascii=False,
            )

        numbers |= extract_is(reference)

    return numbers


def event_text(event):
    parts = []

    for key in (
        "title",
        "order_title",
        "text",
        "evidence",
        "source_text",
        "description",
        "document_title",
    ):
        value = event.get(key)

        if value:
            if isinstance(value, (dict, list)):
                value = json.dumps(
                    value,
                    ensure_ascii=False,
                )

            parts.append(str(value))

    return "\n".join(parts)


def event_is_numbers(event):
    numbers = set()

    for key in (
        "is_numbers",
        "indian_standards",
        "standards",
        "is_number",
        "standard_number",
    ):
        value = event.get(key)

        if isinstance(value, list):
            for item in value:
                numbers |= extract_is(item)

        elif value:
            numbers |= extract_is(value)

    numbers |= extract_is(
        event_text(event)
    )

    return numbers


def event_type(event):
    value = (
        event.get("event_type")
        or event.get("type")
        or "UNKNOWN"
    )

    return normalize(value)


def event_id(event, fallback):
    for key in (
        "document_id",
        "qco_document_id",
        "id",
    ):
        if event.get(key) is not None:
            return str(event[key])

    return str(fallback)


def main():
    standards_data = load(STANDARDS_FILE)
    events_data = load(EVENTS_FILE)

    standards = standards_data.get(
        "standards",
        [],
    )

    events = events_data.get(
        "events",
        [],
    )

    events_by_is = defaultdict(list)

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue

        for is_number in event_is_numbers(event):
            events_by_is[is_number].append(
                (
                    index,
                    event,
                )
            )

    links = []
    seen = set()

    standards_with_qco = 0
    standards_without_qco = 0

    by_relationship = defaultdict(int)

    for standard in standards:
        if not isinstance(standard, dict):
            continue

        standard_id = str(
            standard.get("standard_id")
        )

        is_numbers = standard_numbers(
            standard
        )

        matches = []

        for is_number in is_numbers:
            matches.extend(
                events_by_is.get(
                    is_number,
                    [],
                )
            )

        unique_matches = {}

        for index, event in matches:
            eid = event_id(
                event,
                index,
            )
            unique_matches[eid] = event

        if unique_matches:
            standards_with_qco += 1
        else:
            standards_without_qco += 1

        standard_links = []

        for eid, event in unique_matches.items():
            relationship = event_type(event)

            key = (
                standard_id,
                eid,
                relationship,
            )

            if key in seen:
                continue

            seen.add(key)

            evidence = (
                event.get("evidence")
                or event.get("source_text")
                or event.get("text")
                or ""
            )

            link = {
                "standard_id": standard_id,
                "standard_number": standard.get(
                    "standard_number"
                ),
                "qco_document_id": eid,
                "relationship": relationship,
                "matched_is_numbers": sorted(
                    standard_numbers(standard)
                    & event_is_numbers(event)
                ),
                "order_number": event.get(
                    "order_number"
                ),
                "order_date": event.get(
                    "order_date"
                ),
                "evidence": str(evidence)[:1500],
                "source": event.get(
                    "source"
                ),
                "confidence": "high",
            }

            links.append(link)
            standard_links.append(link)

            by_relationship[relationship] += 1

    output = {
        "source": "BIS Official QCO + Standards datasets",
        "generated_at": now(),
        "standard_count": len(standards),
        "qco_event_count": len(events),
        "link_count": len(links),
        "standards_with_qco": standards_with_qco,
        "standards_without_qco": standards_without_qco,
        "links": links,
    }

    audit = {
        "generated_at": now(),
        "standards": len(standards),
        "qco_events": len(events),
        "links": len(links),
        "standards_with_qco": standards_with_qco,
        "standards_without_qco": standards_without_qco,
        "relationships": dict(
            sorted(by_relationship.items())
        ),
        "status": "completed",
    }

    save(
        OUTPUT_FILE,
        output,
    )

    save(
        AUDIT_FILE,
        audit,
    )

    print("=" * 60)
    print("STANDARD ↔ QCO MAPPING COMPLETE")
    print("=" * 60)
    print(f"Standards:          {len(standards)}")
    print(f"QCO events:         {len(events)}")
    print(f"Links:              {len(links)}")
    print(
        f"Standards with QCO: {standards_with_qco}"
    )
    print(
        f"Standards without:  {standards_without_qco}"
    )

    print()
    print("Relationships:")

    for relationship, count in sorted(
        by_relationship.items()
    ):
        print(
            f"  {relationship}: {count}"
        )

    print()
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
