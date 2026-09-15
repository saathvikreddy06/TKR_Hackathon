import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QCO_DIR = ROOT / "data" / "normalized" / "qco"

EVENTS_FILE = QCO_DIR / "qco_events.json"
OUTPUT_FILE = QCO_DIR / "qco_regulatory_state.json"


def main():
    data = json.loads(
        EVENTS_FILE.read_text(encoding="utf-8")
    )

    events = data.get("events", [])

    by_is = defaultdict(list)

    for event in events:
        for is_number in event.get("is_numbers") or []:
            by_is[is_number].append(event)

    states = []

    for is_number, related_events in sorted(
        by_is.items()
    ):
        originals = [
            e for e in related_events
            if e["event_type"] == "ORIGINAL_QCO"
        ]

        amendments = [
            e for e in related_events
            if e["event_type"] == "AMENDMENT"
        ]

        extensions = [
            e for e in related_events
            if e["event_type"] == "EXTENSION"
        ]

        rescinds = [
            e for e in related_events
            if e["event_type"] == "RESCIND"
        ]

        exemptions = [
            e for e in related_events
            if e["event_type"] == "EXEMPTION"
        ]

        deferments = [
            e for e in related_events
            if e["event_type"] == "DEFERMENT"
        ]

        corrigenda = [
            e for e in related_events
            if e["event_type"] == "CORRIGENDUM"
        ]

        if rescinds:
            status = "RESCIND_REQUIRES_REVIEW"
        elif deferments:
            status = "DEFERMENT_REQUIRES_REVIEW"
        elif exemptions:
            status = "EXEMPTION_REQUIRES_REVIEW"
        elif extensions:
            status = "EXTENSION_REQUIRES_REVIEW"
        elif amendments:
            status = "AMENDED"
        elif originals:
            status = "QCO_IDENTIFIED"
        else:
            status = "REGULATORY_REFERENCE"

        states.append({
            "is_number": is_number,
            "regulatory_status": status,
            "original_qco_documents": [
                e["document_id"]
                for e in originals
            ],
            "amendment_documents": [
                e["document_id"]
                for e in amendments
            ],
            "extension_documents": [
                e["document_id"]
                for e in extensions
            ],
            "rescind_documents": [
                e["document_id"]
                for e in rescinds
            ],
            "exemption_documents": [
                e["document_id"]
                for e in exemptions
            ],
            "deferment_documents": [
                e["document_id"]
                for e in deferments
            ],
            "corrigendum_documents": [
                e["document_id"]
                for e in corrigenda
            ],
            "source_documents": sorted({
                e["document_id"]
                for e in related_events
            }),
            "event_count": len(related_events),
            "evidence": [
                {
                    "event_id": e["event_id"],
                    "event_type": e["event_type"],
                    "document_id": e["document_id"],
                    "source_url": e.get("source_url"),
                    "evidence": e.get("evidence"),
                    "confidence": e.get("confidence"),
                }
                for e in related_events
                if e.get("evidence")
            ],
        })

    metadata = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_events": len(events),
        "unique_is_numbers": len(states),
        "method": (
            "event aggregation; status indicates "
            "review state and does not assert current "
            "legal validity"
        ),
    }

    OUTPUT_FILE.write_text(
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

    from collections import Counter

    counts = Counter(
        s["regulatory_status"]
        for s in states
    )

    print("BIS QCO REGULATORY STATE")
    print(f"Events:       {len(events)}")
    print(f"IS states:    {len(states)}")
    print()
    print("STATUS")

    for status, count in counts.most_common():
        print(f"  {status:<35} {count}")

    print()
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()