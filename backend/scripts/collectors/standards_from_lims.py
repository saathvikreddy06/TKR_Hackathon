from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

LABS = DATA / "normalized" / "labs"
STANDARDS = DATA / "normalized" / "standards"
MANIFESTS = DATA / "manifests"

TESTS_FILE = LABS / "bis_lims_tests.json"
CAPABILITIES_FILE = LABS / "bis_lims_capabilities.json"

RESOLUTION_FILE = STANDARDS / "lims_standard_resolution.json"
DETAILS_FILE = STANDARDS / "bis_standards_from_lims.json"
MANIFEST_FILE = MANIFESTS / "bis_standards_from_lims_manifest.json"

SEARCH_URL = (
    "https://standardsadmin.bis.gov.in/review-service/"
    "searchKnowStandards"
)

DETAIL_URL = (
    "https://standardsadmin.bis.gov.in/proposal-service/"
    "getStandardsWithDeptAndCommittee"
)

TIMEOUT = 30
RETRIES = 4
SLEEP = 0.2

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
})


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path, default):
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temp = path.with_name(
        f"{path.name}.{time.time_ns()}.tmp"
    )

    temp.write_text(
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

            temp.rename(path)
            return

        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(1)

    raise RuntimeError(f"Could not save {path}")


def request_json(url, payload):
    last_error = None

    for attempt in range(1, RETRIES + 1):
        try:
            response = session.post(
                url,
                json=payload,
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                return response.json()

            last_error = (
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        except Exception as exc:
            last_error = str(exc)

        if attempt < RETRIES:
            time.sleep(attempt * 2)

    raise RuntimeError(last_error or "Request failed")


def normalize_text(value):
    value = str(value or "").upper()
    value = value.replace("\xa0", " ")
    value = value.replace(":", " ")
    value = value.replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_is(value):
    text = normalize_text(value)

    match = re.search(
        r"\bIS\s*(\d{1,6})",
        text,
    )

    if not match:
        return None

    number = match.group(1)

    part = None
    section = None
    year = None

    part_match = re.search(
        r"PART\s*[- ]?\s*(\d+)",
        text,
    )

    section_match = re.search(
        r"(?:SEC|SECTION)\s*[- ]?\s*(\d+)",
        text,
    )

    year_matches = re.findall(
        r"\b(19\d{2}|20\d{2})\b",
        text,
    )

    if part_match:
        part = part_match.group(1)

    if section_match:
        section = section_match.group(1)

    if year_matches:
        year = year_matches[-1]

    return {
        "original": str(value).strip(),
        "number": number,
        "part": part,
        "section": section,
        "year": year,
        "base": f"IS {number}",
    }


def extract_is_numbers():
    parsed = {}

    for path in (
        TESTS_FILE,
        CAPABILITIES_FILE,
    ):
        data = load(path, [])

        if not isinstance(data, list):
            continue

        for row in data:
            if not isinstance(row, dict):
                continue

            value = row.get("indian_standard_no")

            item = parse_is(value)

            if not item:
                continue

            key = (
                item["number"],
                item["part"],
                item["section"],
                item["year"],
            )

            parsed[key] = item

    return list(parsed.values())


def extract_records(data):
    if not isinstance(data, dict):
        return []

    value = data.get("data")

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        for key in (
            "records",
            "results",
            "content",
            "rows",
            "standards",
            "data",
        ):
            if isinstance(value.get(key), list):
                return value[key]

    for key in (
        "records",
        "results",
        "content",
        "rows",
        "standards",
    ):
        if isinstance(data.get(key), list):
            return data[key]

    return []


def candidate_number(record):
    if not isinstance(record, dict):
        return ""

    for key in (
        "standardNumber",
        "standard_no",
        "standardNumberName",
        "isNumber",
        "standard",
    ):
        value = record.get(key)

        if value:
            return normalize_text(value)

    return ""


def candidate_id(record):
    if not isinstance(record, dict):
        return None

    for key in (
        "standardId",
        "pk_is_id",
        "id",
    ):
        if record.get(key) is not None:
            return record[key]

    return None


def candidate_title(record):
    if not isinstance(record, dict):
        return ""

    for key in (
        "standardName",
        "title",
        "name",
    ):
        if record.get(key):
            return str(record[key])

    return ""


def score_candidate(query, record):
    number = candidate_number(record)

    if not number:
        return -1

    score = 0

    query_number = query["number"]

    number_match = re.search(
        rf"\bIS\s*{re.escape(query_number)}\b",
        number,
    )

    if not number_match:
        return -1

    score += 50

    if query["part"]:
        part_pattern = (
            rf"PART\s*[- ]?\s*{re.escape(query['part'])}"
        )

        if re.search(part_pattern, number):
            score += 30

    if query["section"]:
        section_pattern = (
            rf"(?:SEC|SECTION)\s*[- ]?\s*"
            rf"{re.escape(query['section'])}"
        )

        if re.search(section_pattern, number):
            score += 20

    if query["year"]:
        if query["year"] in number:
            score += 20

    return score


SEARCH_PAYLOADS = [
    lambda value: {"searchText": value},
    lambda value: {"search": value},
    lambda value: {"query": value},
    lambda value: {"keyword": value},
    lambda value: {"standardNumber": value},
    lambda value: {"standardNo": value},
    lambda value: {"searchTerm": value},
]


def discover_search_payload(sample):
    print("Discovering BIS search format...")

    for builder in SEARCH_PAYLOADS:
        payload = builder(sample["base"])

        try:
            response = request_json(
                SEARCH_URL,
                payload,
            )

            records = extract_records(response)

            if records:
                print(f"Using search payload: {payload}")
                return builder

        except Exception:
            continue

    raise RuntimeError(
        "Could not determine BIS search request format."
    )


def search_candidates(query, builder):
    search_values = [
        query["original"],
        query["base"],
    ]

    if query["part"]:
        search_values.append(
            f"{query['base']} PART {query['part']}"
        )

    candidates = []

    for value in search_values:
        response = request_json(
            SEARCH_URL,
            builder(value),
        )

        records = extract_records(response)

        for record in records:
            if candidate_id(record) is not None:
                candidates.append(record)

        if candidates:
            break

    return candidates


def choose_candidate(query, candidates):
    scored = []

    seen = set()

    for record in candidates:
        standard_id = candidate_id(record)

        if standard_id is None:
            continue

        key = str(standard_id)

        if key in seen:
            continue

        seen.add(key)

        score = score_candidate(
            query,
            record,
        )

        if score >= 50:
            scored.append(
                (
                    score,
                    record,
                )
            )

    scored.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    if not scored:
        return None, []

    return scored[0][1], scored


def fetch_detail(standard_id):
    return request_json(
        DETAIL_URL,
        {
            "StandardId": standard_id,
        },
    )


def main():
    print("Extracting canonical IS references from LIMS...")

    queries = extract_is_numbers()

    print(f"Unique LIMS references: {len(queries)}")

    if not queries:
        raise RuntimeError(
            "No IS references found in LIMS data."
        )

    resolution = load(
        RESOLUTION_FILE,
        {},
    )

    if isinstance(resolution, dict):
        resolution_records = resolution.get(
            "records",
            resolution,
        )
    else:
        resolution_records = {}

    if not isinstance(resolution_records, dict):
        resolution_records = {}

    payload_builder = discover_search_payload(
        queries[0]
    )

    print()
    print("Resolving standards...")

    for index, query in enumerate(
        queries,
        1,
    ):
        key = (
            f"IS {query['number']}"
            f"|P{query['part'] or '-'}"
            f"|S{query['section'] or '-'}"
            f"|Y{query['year'] or '-'}"
        )

        old = resolution_records.get(key)

        if (
            isinstance(old, dict)
            and old.get("status") == "resolved"
            and old.get("standard_id") is not None
        ):
            continue

        print(
            f"[{index}/{len(queries)}] "
            f"{query['original']}"
        )

        try:
            candidates = search_candidates(
                query,
                payload_builder,
            )

            match, scored = choose_candidate(
                query,
                candidates,
            )

            if not match:
                resolution_records[key] = {
                    "status": "unresolved",
                    "searched_at": now(),
                    "query": query,
                    "candidate_count": len(candidates),
                    "candidates": candidates[:20],
                }
            else:
                resolution_records[key] = {
                    "status": "resolved",
                    "searched_at": now(),
                    "query": query,
                    "standard_id": candidate_id(match),
                    "standard_number": candidate_number(match),
                    "standard_name": candidate_title(match),
                    "score": scored[0][0],
                    "candidate_count": len(candidates),
                    "match": match,
                }

        except Exception as exc:
            resolution_records[key] = {
                "status": "failed",
                "searched_at": now(),
                "query": query,
                "error": str(exc),
            }

        save(
            RESOLUTION_FILE,
            {
                "updated_at": now(),
                "records": resolution_records,
            },
        )

        time.sleep(SLEEP)

    resolved = {
        key: value
        for key, value in resolution_records.items()
        if (
            isinstance(value, dict)
            and value.get("status") == "resolved"
            and value.get("standard_id") is not None
        )
    }

    print()
    print(f"Resolved: {len(resolved)}")
    print("Fetching BIS standard details...")

    details = load(
        DETAILS_FILE,
        {},
    )

    detail_records = (
        details.get("records", {})
        if isinstance(details, dict)
        else {}
    )

    if not isinstance(detail_records, dict):
        detail_records = {}

    resolved_items = list(
        resolved.items()
    )

    for index, (
        resolution_key,
        resolution_record,
    ) in enumerate(
        resolved_items,
        1,
    ):
        standard_id = resolution_record[
            "standard_id"
        ]

        key = str(standard_id)

        old = detail_records.get(key)

        if (
            isinstance(old, dict)
            and old.get("status") == "success"
            and old.get("data")
        ):
            continue

        print(
            f"[DETAIL {index}/{len(resolved_items)}] "
            f"{resolution_record.get('standard_number')}"
        )

        try:
            data = fetch_detail(
                standard_id
            )

            detail_records[key] = {
                "status": "success",
                "retrieved_at": now(),
                "standard_id": standard_id,
                "lims_reference": resolution_record[
                    "query"
                ],
                "standard_number": resolution_record[
                    "standard_number"
                ],
                "source_url": DETAIL_URL,
                "data": data,
            }

        except Exception as exc:
            detail_records[key] = {
                "status": "failed",
                "retrieved_at": now(),
                "standard_id": standard_id,
                "lims_reference": resolution_record[
                    "query"
                ],
                "error": str(exc),
            }

        save(
            DETAILS_FILE,
            {
                "source": "BIS Standards Portal",
                "updated_at": now(),
                "records": detail_records,
            },
        )

        time.sleep(SLEEP)

    success = sum(
        1
        for record in detail_records.values()
        if (
            isinstance(record, dict)
            and record.get("status") == "success"
        )
    )

    unresolved = sum(
        1
        for record in resolution_records.values()
        if (
            isinstance(record, dict)
            and record.get("status") == "unresolved"
        )
    )

    failed = sum(
        1
        for record in resolution_records.values()
        if (
            isinstance(record, dict)
            and record.get("status") == "failed"
        )
    )

    save(
        MANIFEST_FILE,
        {
            "source": "BIS Standards Portal",
            "search_url": SEARCH_URL,
            "detail_url": DETAIL_URL,
            "retrieved_at": now(),
            "lims_unique_references": len(queries),
            "resolved": len(resolved),
            "unresolved": unresolved,
            "resolution_failed": failed,
            "detail_success": success,
            "status": "partial" if unresolved or failed else "completed",
        },
    )

    print()
    print("=" * 60)
    print("BIS STANDARDS RESOLUTION COMPLETE")
    print("=" * 60)
    print(f"LIMS references: {len(queries)}")
    print(f"Resolved:        {len(resolved)}")
    print(f"Unresolved:      {unresolved}")
    print(f"Resolution fail: {failed}")
    print(f"Details success: {success}")


if __name__ == "__main__":
    main()
