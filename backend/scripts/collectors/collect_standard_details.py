import json
import os
import time
from datetime import datetime, timezone

import requests

BASE_URL = "https://standardsadmin.bis.gov.in/proposal-service/getStandardsWithDeptAndCommittee"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

INPUT_FILE = os.path.join(
    ROOT, "normalized", "standards", "bis_standards_master.json"
)

OUTPUT_FILE = os.path.join(
    ROOT, "normalized", "standards", "bis_standards_details.json"
)

CHECKPOINT_FILE = os.path.join(
    ROOT, "manifests", "bis_standards_details_checkpoint.json"
)

MANIFEST_FILE = os.path.join(
    ROOT, "manifests", "bis_standards_details_manifest.json"
)

SAVE_EVERY = 25
MAX_RETRIES = 4
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_REQUESTS = 0.15


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    temp = f"{path}.tmp.{os.getpid()}"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    for attempt in range(5):
        try:
            if os.path.exists(path):
                os.unlink(path)
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.5)


def extract_payload(response):
    data = response.json()

    if isinstance(data, dict) and "data" in data:
        return data["data"]

    return data


def fetch_details(session, standard_id):
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.post(
                BASE_URL,
                json={"StandardId": standard_id},
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()
            return extract_payload(response)

        except Exception as exc:
            last_error = str(exc)

            if attempt < MAX_RETRIES:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(last_error)


def main():
    print("=" * 60)
    print("BIS STANDARD DETAILS COLLECTION")
    print("=" * 60)

    master = load_json(INPUT_FILE, None)

    if not isinstance(master, dict):
        raise RuntimeError("Invalid BIS standards master structure")

    catalogue = master.get("standards")

    if not isinstance(catalogue, list):
        raise RuntimeError(
            "Expected 'standards' list in bis_standards_master.json"
        )

    print(f"Master records: {len(catalogue)}")

    checkpoint = load_json(
        CHECKPOINT_FILE,
        {
            "completed": [],
            "failed": {},
            "last_index": 0,
            "updated_at": None,
        },
    )

    results = load_json(OUTPUT_FILE, {})

    if not isinstance(results, dict):
        results = {}

    completed = set(str(x) for x in checkpoint.get("completed", []))
    failed = checkpoint.get("failed", {})

    remaining = []

    for index, record in enumerate(catalogue):
        if not isinstance(record, dict):
            continue

        standard_id = record.get("standard_id")

        if standard_id is None:
            continue

        key = str(standard_id)

        if key not in completed:
            remaining.append((index, record))

    print(f"Already completed: {len(completed)}")
    print(f"Remaining:         {len(remaining)}")
    print(f"Previous failures: {len(failed)}")
    print()

    if not remaining:
        print("Nothing to collect.")
        return

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://standards.bis.gov.in",
            "Referer": "https://standards.bis.gov.in/",
        }
    )

    for position, (index, record) in enumerate(remaining, start=1):
        standard_id = record["standard_id"]
        key = str(standard_id)

        print(
            f"[{position}/{len(remaining)}] "
            f"IS={record.get('standard_number')} "
            f"ID={standard_id}"
        )

        try:
            details = fetch_details(session, standard_id)

            results[key] = {
                "standard_id": standard_id,
                "standard_number": record.get("standard_number"),
                "details": details,
                "retrieved_at": utc_now(),
            }

            completed.add(key)
            failed.pop(key, None)

        except Exception as exc:
            failed[key] = {
                "standard_id": standard_id,
                "standard_number": record.get("standard_number"),
                "error": str(exc),
                "failed_at": utc_now(),
            }

            print(f"  FAILED: {exc}")

        checkpoint["completed"] = sorted(completed)
        checkpoint["failed"] = failed
        checkpoint["last_index"] = index
        checkpoint["updated_at"] = utc_now()

        if position % SAVE_EVERY == 0:
            atomic_write(OUTPUT_FILE, results)
            atomic_write(CHECKPOINT_FILE, checkpoint)

            print(
                f"  Saved: {len(completed)} completed, "
                f"{len(failed)} failed"
            )

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    atomic_write(OUTPUT_FILE, results)
    atomic_write(CHECKPOINT_FILE, checkpoint)

    manifest = {
        "source": "BIS Standards Portal",
        "source_type": "BIS_OFFICIAL",
        "endpoint": BASE_URL,
        "master_records": len(catalogue),
        "completed": len(completed),
        "failed": len(failed),
        "output": OUTPUT_FILE,
        "checkpoint": CHECKPOINT_FILE,
        "retrieved_at": utc_now(),
    }

    atomic_write(MANIFEST_FILE, manifest)

    print()
    print("=" * 60)
    print("BIS STANDARD DETAILS COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Master records: {len(catalogue)}")
    print(f"Completed:      {len(completed)}")
    print(f"Failed:         {len(failed)}")
    print(f"Output:         {OUTPUT_FILE}")
    print(f"Checkpoint:     {CHECKPOINT_FILE}")


if __name__ == "__main__":
    main()
