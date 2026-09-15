import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

RESOLUTION_FILE = (
    DATA / "normalized" / "standards"
    / "lims_standard_resolution.json"
)

DETAILS_FILE = (
    DATA / "normalized" / "standards"
    / "bis_standards_from_lims.json"
)

OUTPUT_FILE = (
    DATA / "normalized" / "standards"
    / "bis_standards.json"
)

AUDIT_FILE = (
    DATA / "manifests"
    / "bis_standards_normalization_manifest.json"
)


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temp = path.with_name(
        f"{path.name}.{datetime.now().timestamp()}.tmp"
    )

    temp.write_text(
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
            temp.rename(path)
            return
        except PermissionError:
            import time
            time.sleep(1)

    raise PermissionError(f"Could not replace {path}")


def main():
    resolution_data = load(RESOLUTION_FILE)
    detail_data = load(DETAILS_FILE)

    resolutions = resolution_data.get(
        "records",
        resolution_data,
    )

    details = detail_data.get(
        "records",
        detail_data,
    )

    by_standard_id = defaultdict(list)

    for resolution_key, record in resolutions.items():
        if not isinstance(record, dict):
            continue

        if record.get("status") != "resolved":
            continue

        standard_id = record.get("standard_id")

        if standard_id is None:
            continue

        by_standard_id[str(standard_id)].append(
            {
                "resolution_key": resolution_key,
                "lims_reference": record.get("query"),
                "standard_number": record.get(
                    "standard_number"
                ),
                "standard_name": record.get(
                    "standard_name"
                ),
                "score": record.get("score"),
            }
        )

    standards = []

    missing_details = []
    duplicate_mapping_count = 0

    for standard_id, mappings in by_standard_id.items():
        detail = details.get(standard_id)

        if not isinstance(detail, dict):
            missing_details.append(standard_id)
            continue

        if detail.get("status") != "success":
            missing_details.append(standard_id)
            continue

        raw = detail.get("data")

        standard = {
            "standard_id": standard_id,
            "standard_number": (
                mappings[0].get("standard_number")
                or detail.get("standard_number")
            ),
            "title": (
                mappings[0].get("standard_name")
                or detail.get("standard_number")
            ),
            "lims_references": [],
            "mapping_count": len(mappings),
            "source": {
                "source_type": "BIS_OFFICIAL",
                "source_url": detail.get(
                    "source_url"
                ),
            },
            "raw": raw,
        }

        seen_refs = set()

        for mapping in mappings:
            reference = mapping.get("lims_reference")
            if isinstance(reference, dict):
                reference = json.dumps(
                    reference,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            elif isinstance(reference, list):
                reference = json.dumps(
                    reference,
                    ensure_ascii=False,
                )
            elif reference is not None:
                reference = str(reference)

            if reference and reference not in seen_refs:
                seen_refs.add(reference)
                standard["lims_references"].append(reference)

        if len(mappings) > 1:
            duplicate_mapping_count += (
                len(mappings) - 1
            )

        standards.append(standard)

    standards.sort(
        key=lambda x: (
            x.get("standard_number") or "",
            x.get("standard_id") or "",
        )
    )

    output = {
        "source": "BIS Official Standards Portal",
        "generated_at": now(),
        "standard_count": len(standards),
        "standards": standards,
    }

    save(
        OUTPUT_FILE,
        output,
    )

    audit = {
        "source": "BIS Official Standards Portal",
        "generated_at": now(),
        "resolution_records": len(
            [
                r
                for r in resolutions.values()
                if isinstance(r, dict)
                and r.get("status") == "resolved"
            ]
        ),
        "unique_standard_ids": len(
            by_standard_id
        ),
        "unique_master_records": len(
            standards
        ),
        "duplicate_mappings": duplicate_mapping_count,
        "missing_details": len(
            missing_details
        ),
        "missing_detail_ids": missing_details,
        "status": (
            "completed"
            if not missing_details
            else "partial"
        ),
    }

    save(
        AUDIT_FILE,
        audit,
    )

    print("=" * 60)
    print("BIS STANDARDS NORMALIZATION COMPLETE")
    print("=" * 60)
    print(
        f"Resolution records:  {audit['resolution_records']}"
    )
    print(
        f"Unique Standard IDs: {audit['unique_standard_ids']}"
    )
    print(
        f"Master records:      {audit['unique_master_records']}"
    )
    print(
        f"Duplicate mappings:  {audit['duplicate_mappings']}"
    )
    print(
        f"Missing details:     {audit['missing_details']}"
    )
    print()
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
