import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CATALOGUE_FILE = (
    DATA / "normalized" / "standards"
    / "bis_standards_catalogue.json"
)

ENRICHED_FILE = (
    DATA / "normalized" / "standards"
    / "bis_standards.json"
)

OUTPUT_FILE = (
    DATA / "normalized" / "standards"
    / "bis_standards_master.json"
)

AUDIT_FILE = (
    DATA / "manifests"
    / "bis_standards_master_manifest.json"
)


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save(path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_name(
        f"{path.name}.{time.time_ns()}.tmp"
    )

    tmp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for attempt in range(5):
        try:
            if path.exists():
                path.unlink()

            tmp.rename(path)
            return

        except PermissionError:
            if attempt == 4:
                raise

            time.sleep(1)


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


def standard_numbers(record):
    numbers = set()

    numbers |= extract_is(
        record.get("standard_number")
    )

    numbers |= extract_is(
        record.get("standardNumber")
    )

    numbers |= extract_is(
        record.get("standard_name")
    )

    numbers |= extract_is(
        record.get("standardName")
    )

    numbers |= extract_is(
        record.get("standard_label")
    )

    for reference in record.get(
        "lims_references",
        [],
    ):
        numbers |= extract_is(
            reference
        )

    return numbers


def main():
    catalogue_data = load(
        CATALOGUE_FILE
    )

    enriched_data = load(
        ENRICHED_FILE
    )

    catalogue = catalogue_data.get(
        "standards",
        [],
    )

    enriched = enriched_data.get(
        "standards",
        [],
    )

    print("=" * 60)
    print("BUILDING BIS STANDARDS MASTER")
    print("=" * 60)
    print(
        f"Catalogue records: {len(catalogue)}"
    )
    print(
        f"LIMS enriched:     {len(enriched)}"
    )
    print()

    by_id = {}

    duplicate_catalogue_ids = 0

    for record in catalogue:
        if not isinstance(record, dict):
            continue

        sid = record.get(
            "standard_id"
        )

        if sid is None:
            continue

        key = str(sid)

        if key in by_id:
            duplicate_catalogue_ids += 1
            continue

        by_id[key] = record

    enriched_by_id = {}

    for record in enriched:
        if not isinstance(record, dict):
            continue

        sid = record.get(
            "standard_id"
        )

        if sid is None:
            continue

        enriched_by_id[str(sid)] = record

    exact_id_matches = 0

    for sid in enriched_by_id:
        if sid in by_id:
            exact_id_matches += 1

    catalogue_by_is = defaultdict(list)

    for record in catalogue:
        if not isinstance(record, dict):
            continue

        sid = record.get(
            "standard_id"
        )

        if sid is None:
            continue

        for number in standard_numbers(
            record
        ):
            catalogue_by_is[number].append(
                str(sid)
            )

    enriched_is_matches = 0
    ambiguous_is_matches = 0
    unmatched_enriched = []

    enriched_to_catalogue = {}

    for record in enriched:
        if not isinstance(record, dict):
            continue

        sid = record.get(
            "standard_id"
        )

        if sid is None:
            continue

        sid = str(sid)

        if sid in by_id:
            enriched_to_catalogue[sid] = sid
            continue

        candidates = set()

        for number in standard_numbers(
            record
        ):
            candidates.update(
                catalogue_by_is.get(
                    number,
                    [],
                )
            )

        if len(candidates) == 1:
            target = next(
                iter(candidates)
            )

            enriched_to_catalogue[sid] = (
                target
            )

            enriched_is_matches += 1

        elif len(candidates) > 1:
            ambiguous_is_matches += 1

        else:
            unmatched_enriched.append(
                sid
            )

    master = []

    enriched_master_count = 0

    for sid, catalogue_record in by_id.items():
        enriched_record = (
            enriched_by_id.get(sid)
        )

        if enriched_record:
            enriched_master_count += 1

        record = {
            "standard_id": sid,
            "standard_number": (
                catalogue_record.get(
                    "standard_number"
                )
                or (
                    enriched_record or {}
                ).get(
                    "standard_number"
                )
            ),
            "title": (
                catalogue_record.get(
                    "standard_name"
                )
                or catalogue_record.get(
                    "standard_label"
                )
                or (
                    enriched_record or {}
                ).get(
                    "title"
                )
            ),
            "department": (
                catalogue_record.get(
                    "department"
                )
                or (
                    enriched_record or {}
                ).get(
                    "department"
                )
            ),
            "sectional_committee": (
                catalogue_record.get(
                    "sectional_committee"
                )
            ),
            "type": (
                catalogue_record.get(
                    "type"
                )
            ),
            "published_on": (
                catalogue_record.get(
                    "published_on"
                )
            ),
            "standard_enc_id": (
                catalogue_record.get(
                    "standard_enc_id"
                )
            ),
            "enrichment": {
                "lims_enriched": bool(
                    enriched_record
                ),
            },
            "catalogue": catalogue_record,
            "lims_detail": (
                enriched_record
                if enriched_record
                else None
            ),
        }

        master.append(record)

    master.sort(
        key=lambda record: (
            record.get(
                "standard_number"
            )
            or "",
            str(
                record.get(
                    "standard_id"
                )
            ),
        )
    )

    catalogue_ids = set(
        by_id.keys()
    )

    enriched_ids = set(
        enriched_by_id.keys()
    )

    catalogue_only = (
        catalogue_ids
        - enriched_ids
    )

    audit = {
        "generated_at": now(),
        "catalogue_records": len(
            catalogue
        ),
        "unique_catalogue_ids": len(
            catalogue_ids
        ),
        "enriched_records": len(
            enriched
        ),
        "unique_enriched_ids": len(
            enriched_ids
        ),
        "master_records": len(
            master
        ),
        "exact_standard_id_matches": (
            exact_id_matches
        ),
        "is_number_matches": (
            enriched_is_matches
        ),
        "ambiguous_is_matches": (
            ambiguous_is_matches
        ),
        "unmatched_enriched": len(
            unmatched_enriched
        ),
        "catalogue_only": len(
            catalogue_only
        ),
        "duplicate_catalogue_ids": (
            duplicate_catalogue_ids
        ),
        "status": "completed",
    }

    output = {
        "source": (
            "BIS Official Standards "
            "Catalogue + LIMS enrichment"
        ),
        "generated_at": now(),
        "master_count": len(master),
        "standards": master,
    }

    save(
        OUTPUT_FILE,
        output,
    )

    save(
        AUDIT_FILE,
        audit,
    )

    print()
    print("=" * 60)
    print("BIS STANDARDS MASTER COMPLETE")
    print("=" * 60)
    print(
        f"Unique catalogue IDs: "
        f"{audit['unique_catalogue_ids']}"
    )
    print(
        f"Unique enriched IDs:  "
        f"{audit['unique_enriched_ids']}"
    )
    print(
        f"Master records:        "
        f"{audit['master_records']}"
    )
    print(
        f"Exact ID matches:      "
        f"{audit['exact_standard_id_matches']}"
    )
    print(
        f"IS-number matches:     "
        f"{audit['is_number_matches']}"
    )
    print(
        f"Ambiguous IS matches:  "
        f"{audit['ambiguous_is_matches']}"
    )
    print(
        f"Unmatched enriched:    "
        f"{audit['unmatched_enriched']}"
    )
    print(
        f"Catalogue only:        "
        f"{audit['catalogue_only']}"
    )
    print(
        f"Duplicate catalogue IDs:"
        f" {audit['duplicate_catalogue_ids']}"
    )
    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
