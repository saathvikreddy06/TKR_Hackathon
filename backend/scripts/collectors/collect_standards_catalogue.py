import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

OUTPUT = (
    DATA / "normalized" / "standards"
    / "bis_standards_catalogue.json"
)

CHECKPOINT = (
    DATA / "manifests"
    / "bis_standards_catalogue_checkpoint.json"
)

URL = (
    "https://standardsadmin.bis.gov.in/"
    "proposal-service/getWebsiteIndianStandardsList"
)

PAGE_SIZE = 100
TIMEOUT = 30
RETRIES = 4
SLEEP = 0.25


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path, default):
    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return default


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


def request_page(session, page):
    payload = {
        "page": page,
        "pageSize": PAGE_SIZE,
    }

    last_error = None

    for attempt in range(1, RETRIES + 1):
        try:
            response = session.post(
                URL,
                json=payload,
                timeout=TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            if not isinstance(data, dict):
                raise RuntimeError(
                    "Unexpected API response."
                )

            if data.get("statusCode") != 200:
                raise RuntimeError(
                    data.get("msg")
                    or "BIS API returned an error."
                )

            return data

        except Exception as exc:
            last_error = str(exc)

            if attempt < RETRIES:
                time.sleep(
                    min(2 ** attempt, 8)
                )

    raise RuntimeError(
        f"Page {page} failed: {last_error}"
    )


def normalize_record(record):
    if not isinstance(record, dict):
        return None

    standard_id = record.get(
        "standardId"
    )

    if standard_id is None:
        return None

    return {
        "standard_id": standard_id,
        "standard_enc_id": record.get(
            "standardEncId"
        ),
        "standard_number": record.get(
            "standardNumber"
        ),
        "standard_label": record.get(
            "standardLabel"
        ),
        "standard_name": record.get(
            "standardName"
        ),
        "department": record.get(
            "departmentName"
        ),
        "sectional_committee": record.get(
            "sectionalCommitteeName"
        ),
        "type": record.get(
            "typeOfStandardName"
        ),
        "published_on": record.get(
            "publishedOn"
        ),
        "published_on_formatted": record.get(
            "publishedOnFormatted"
        ),
        "source": "BIS_OFFICIAL",
    }


def main():
    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })

    checkpoint = load(
        CHECKPOINT,
        {},
    )

    records = load(
        OUTPUT,
        {},
    )

    existing = records.get(
        "standards",
        [],
    )

    by_id = {}

    for record in existing:
        if isinstance(record, dict):
            sid = record.get(
                "standard_id"
            )

            if sid is not None:
                by_id[str(sid)] = record

    next_page = int(
        checkpoint.get(
            "next_page",
            1,
        )
    )

    total_record = checkpoint.get(
        "total_record"
    )

    print("=" * 60)
    print("BIS PUBLISHED STANDARDS COLLECTION")
    print("=" * 60)

    print(
        f"Existing records: {len(by_id)}"
    )
    print(
        f"Starting page:    {next_page}"
    )

    while True:
        print(
            f"\nFetching page {next_page}"
            + (
                f" / ~{total_record}"
                if total_record
                else ""
            )
        )

        try:
            response = request_page(
                session,
                next_page,
            )
        except Exception as exc:
            checkpoint.update({
                "status": "paused",
                "paused_at": now(),
                "next_page": next_page,
                "total_record": total_record,
                "collected_records": len(
                    by_id
                ),
                "error": str(exc),
            })

            save(
                CHECKPOINT,
                checkpoint,
            )

            print()
            print(
                "Collection paused safely."
            )
            print(
                f"Resume page: {next_page}"
            )
            print(
                f"Reason: {exc}"
            )
            return

        page_records = response.get(
            "data",
            [],
        )

        total_record = response.get(
            "totalRecord",
            total_record,
        )

        api_page = response.get(
            "page",
            next_page,
        )

        api_page_size = response.get(
            "pageSize",
            PAGE_SIZE,
        )

        has_more = response.get(
            "hasMore",
            False,
        )

        added = 0

        for raw in page_records:
            record = normalize_record(
                raw
            )

            if not record:
                continue

            sid = str(
                record["standard_id"]
            )

            if sid not in by_id:
                added += 1

            by_id[sid] = record

        output = {
            "source": (
                "BIS Official Published "
                "Standards Catalogue"
            ),
            "endpoint": URL,
            "updated_at": now(),
            "total_record_reported": total_record,
            "collected_records": len(
                by_id
            ),
            "standards": list(
                by_id.values()
            ),
        }

        save(
            OUTPUT,
            output,
        )

        checkpoint = {
            "status": (
                "running"
                if has_more
                else "completed"
            ),
            "updated_at": now(),
            "last_completed_page": api_page,
            "next_page": (
                int(api_page) + 1
                if has_more
                else None
            ),
            "page_size": api_page_size,
            "total_record": total_record,
            "collected_records": len(
                by_id
            ),
        }

        save(
            CHECKPOINT,
            checkpoint,
        )

        print(
            f"Records returned: {len(page_records)}"
        )
        print(
            f"New records:      {added}"
        )
        print(
            f"Total collected:  {len(by_id)}"
        )
        print(
            f"Has more:         {has_more}"
        )

        if not has_more:
            break

        next_page = int(api_page) + 1

        time.sleep(SLEEP)

    print()
    print("=" * 60)
    print("BIS STANDARDS COLLECTION COMPLETE")
    print("=" * 60)
    print(
        f"Reported by BIS: {total_record}"
    )
    print(
        f"Collected:       {len(by_id)}"
    )
    print(
        f"Last page:       {api_page}"
    )
    print()
    print(
        f"Output: {OUTPUT}"
    )
    print(
        f"Checkpoint: {CHECKPOINT}"
    )


if __name__ == "__main__":
    main()
