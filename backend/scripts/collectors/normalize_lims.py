import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[2]

LABS_JSON = BASE_DIR / "data/normalized/labs/bis_lims_recognized_labs.json"
RAW_DIR = BASE_DIR / "data/raw/labs/scopes"
OUT_DIR = BASE_DIR / "data/normalized/labs"
MANIFEST_DIR = BASE_DIR / "data/manifests"

OUT_LABS = OUT_DIR / "bis_lims_labs.json"
OUT_CAPABILITIES = OUT_DIR / "bis_lims_capabilities.json"
OUT_TESTS = OUT_DIR / "bis_lims_tests.json"
OUT_MANIFEST = MANIFEST_DIR / "bis_lims_normalized_manifest.json"


def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def norm(value):
    return clean(value).casefold()


def now():
    return datetime.now(timezone.utc).isoformat()


def hash_value(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True
        ).encode("utf-8")
    ).hexdigest()


def scope_id(url):
    path = urlparse(clean(url)).path.rstrip("/")
    return path.split("/")[-1]


def load_labs():
    with open(LABS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = (
            data.get("laboratories")
            or data.get("labs")
            or data.get("data")
        )

    if not isinstance(data, list):
        raise ValueError("Invalid laboratory JSON")

    return data


def direct_rows(table):
    rows = []

    for tr in table.find_all("tr"):
        if tr.find_parent("table") is not table:
            continue

        cells = tr.find_all(["th", "td"], recursive=False)

        if not cells:
            continue

        values = [
            clean(cell.get_text(" ", strip=True))
            for cell in cells
        ]

        if any(values):
            rows.append((tr, values))

    return rows


def header_type(values):
    h = {norm(x) for x in values}

    if (
        any("indian standard no" in x for x in h)
        and "product" in h
        and any("testing charges" in x for x in h)
        and "validity date" in h
    ):
        return "capability"

    if (
        any(x.startswith("clause no") for x in h)
        and "exclusion" in h
        and any("testing charges" in x for x in h)
        and "effective date" in h
    ):
        return "test"

    return None


def column_map(headers):
    result = {}

    for i, header in enumerate(headers):
        h = norm(header)

        if "indian standard no" in h:
            result["standard"] = i
        elif h == "product":
            result["product"] = i
        elif (
            "grade / type / size / designation" in h
            or "grade/type/size/designation" in h
        ):
            result["designation"] = i
        elif h == "exclusion":
            result["exclusion"] = i
        elif "testing charges" in h:
            result["charge"] = i
        elif h == "facility type":
            result["facility"] = i
        elif h == "effective date":
            result["effective"] = i
        elif h == "validity date":
            result["validity"] = i
        elif h == "remark":
            result["remark"] = i
        elif h.startswith("clause no"):
            result["clause"] = i

    return result


def value(values, mapping, key):
    i = mapping.get(key)

    if i is None or i >= len(values):
        return ""

    return clean(values[i])


def charge(value_raw):
    raw = clean(value_raw)

    if not raw:
        return None

    match = re.search(
        r"(?<![\d.])(\d+(?:\.\d{1,2})?)(?![\d.])",
        raw.replace(",", "")
    )

    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def is_standard(value):
    return bool(
        re.search(
            r"\bIS\s*\d{2,6}\b",
            clean(value),
            re.I
        )
    )


def capability_from_row(values, mapping):
    standard = value(values, mapping, "standard")
    product = value(values, mapping, "product")

    if not is_standard(standard) or not product:
        return None

    validity = value(values, mapping, "validity")
    remark = value(values, mapping, "remark")

    if norm(validity) in {"clause no.", "clause no"}:
        validity = ""

    if norm(remark) in {"exclusion", "remark"}:
        remark = ""

    charge_raw = value(values, mapping, "charge")

    return {
        "indian_standard_no": standard,
        "product": product,
        "designation": value(values, mapping, "designation"),
        "exclusion": value(values, mapping, "exclusion"),
        "testing_charge": charge(charge_raw),
        "testing_charge_raw": charge_raw,
        "facility_type": value(values, mapping, "facility"),
        "effective_date": value(values, mapping, "effective"),
        "validity_date": validity,
        "remark": remark
    }


def test_from_row(values, mapping, capability):
    clause = value(values, mapping, "clause")

    if not clause:
        return None

    if norm(clause).startswith("clause no"):
        return None

    charge_raw = value(values, mapping, "charge")

    return {
        "indian_standard_no": capability["indian_standard_no"],
        "product": capability["product"],
        "designation": capability["designation"],
        "clause_raw": clause,
        "exclusion": value(values, mapping, "exclusion"),
        "testing_charge": charge(charge_raw),
        "testing_charge_raw": charge_raw,
        "effective_date": value(values, mapping, "effective"),
        "remark": value(values, mapping, "remark")
    }


def find_main_tables(soup):
    result = []

    for table in soup.find_all("table"):
        rows = direct_rows(table)

        for _, values in rows[:8]:
            if header_type(values) == "capability":
                result.append((table, rows))
                break

    return result


def parse_page(html, lab):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    capabilities = []
    tests = []

    main_tables = find_main_tables(soup)

    capability_count = 0
    test_table_count = 0

    for table, rows in main_tables:
        header = None
        header_index = None

        for i, (_, values) in enumerate(rows):
            if header_type(values) == "capability":
                header = values
                header_index = i
                break

        if header is None:
            continue

        cmap = column_map(header)

        for tr, values in rows[header_index + 1:]:
            capability = capability_from_row(values, cmap)

            if capability is None:
                continue

            capability_count += 1

            capability["source_row"] = values

            nested_tables = tr.find_all("table")

            local_test_count = 0

            for nested in nested_tables:
                nested_rows = direct_rows(nested)

                if not nested_rows:
                    continue

                test_header = None
                test_start = None

                for i, (_, nested_values) in enumerate(nested_rows):
                    if header_type(nested_values) == "test":
                        test_header = nested_values
                        test_start = i
                        break

                if test_header is None:
                    continue

                test_table_count += 1
                tmap = column_map(test_header)

                for _, test_values in nested_rows[test_start + 1:]:
                    test = test_from_row(
                        test_values,
                        tmap,
                        capability
                    )

                    if test is None:
                        continue

                    tests.append(test)
                    local_test_count += 1

            capability["test_count"] = local_test_count
            capabilities.append(capability)

    return capabilities, tests, {
        "capability_tables": len(main_tables),
        "capability_rows": capability_count,
        "test_tables": test_table_count,
        "test_rows": len(tests)
    }


def finalize_capability(capability, lab, raw_file, timestamp):
    data = {
        "lab_code": clean(lab.get("lab_code")),
        "lab_name": clean(lab.get("lab_name")),
        "indian_standard_no": capability["indian_standard_no"],
        "product": capability["product"],
        "designation": capability["designation"],
        "exclusion": capability["exclusion"],
        "testing_charge": capability["testing_charge"],
        "testing_charge_raw": capability["testing_charge_raw"],
        "facility_type": capability["facility_type"],
        "effective_date": capability["effective_date"],
        "validity_date": capability["validity_date"],
        "remark": capability["remark"],
        "test_count": capability["test_count"],
        "scope_id": scope_id(lab.get("scope_url")),
        "scope_url": clean(lab.get("scope_url")),
        "raw_file": str(
            raw_file.relative_to(BASE_DIR)
        ).replace("\\", "/"),
        "retrieved_at": timestamp,
        "source": "BIS_LIMS"
    }

    identity = "|".join([
        data["scope_id"],
        data["indian_standard_no"],
        data["product"],
        data["designation"]
    ])

    data["capability_id"] = (
        "LIMS-CAP-" + hashlib.sha256(
            identity.encode()
        ).hexdigest()[:16].upper()
    )

    data["record_hash"] = hash_value(data)

    return data


def finalize_test(test, capability, lab, raw_file, timestamp):
    data = {
        "lab_code": clean(lab.get("lab_code")),
        "lab_name": clean(lab.get("lab_name")),
        "indian_standard_no": test["indian_standard_no"],
        "product": test["product"],
        "designation": test["designation"],
        "clause_raw": test["clause_raw"],
        "exclusion": test["exclusion"],
        "testing_charge": test["testing_charge"],
        "testing_charge_raw": test["testing_charge_raw"],
        "effective_date": test["effective_date"],
        "remark": test["remark"],
        "scope_id": scope_id(lab.get("scope_url")),
        "scope_url": clean(lab.get("scope_url")),
        "capability_id": capability["capability_id"],
        "raw_file": str(
            raw_file.relative_to(BASE_DIR)
        ).replace("\\", "/"),
        "retrieved_at": timestamp,
        "source": "BIS_LIMS"
    }

    identity = "|".join([
        data["scope_id"],
        data["capability_id"],
        data["clause_raw"],
        data["exclusion"],
        data["testing_charge_raw"],
        data["effective_date"],
        data["remark"]
    ])

    data["test_id"] = (
        "LIMS-TEST-" + hashlib.sha256(
            identity.encode()
        ).hexdigest()[:16].upper()
    )

    data["record_hash"] = hash_value(data)

    return data


def main():
    print("=" * 70)
    print("BIS LIMS NORMALIZATION v4")
    print("=" * 70)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    labs = load_labs()

    all_labs = []
    all_capabilities = []
    all_tests = []
    manifest = []

    timestamp = now()

    stats = {
        "labs": len(labs),
        "labs_with_html": 0,
        "labs_without_html": 0,
        "capability_tables": 0,
        "capability_rows": 0,
        "test_tables": 0,
        "test_rows": 0,
        "parse_errors": 0
    }

    for index, lab in enumerate(labs, 1):
        sid = scope_id(lab.get("scope_url"))

        if not sid:
            stats["labs_without_html"] += 1
            continue

        raw_file = RAW_DIR / f"{sid}.html"

        if not raw_file.exists():
            stats["labs_without_html"] += 1
            manifest.append({
                "scope_id": sid,
                "lab_code": clean(lab.get("lab_code")),
                "lab_name": clean(lab.get("lab_name")),
                "scope_url": clean(lab.get("scope_url")),
                "status": "missing"
            })
            continue

        stats["labs_with_html"] += 1

        try:
            html = raw_file.read_text(
                encoding="utf-8",
                errors="replace"
            )

            capabilities, tests, page_stats = parse_page(
                html,
                lab
            )

            stats["capability_tables"] += page_stats[
                "capability_tables"
            ]
            stats["capability_rows"] += page_stats[
                "capability_rows"
            ]
            stats["test_tables"] += page_stats[
                "test_tables"
            ]
            stats["test_rows"] += page_stats[
                "test_rows"
            ]

            finalized_capabilities = []

            for capability in capabilities:
                finalized = finalize_capability(
                    capability,
                    lab,
                    raw_file,
                    timestamp
                )

                finalized_capabilities.append(
                    finalized
                )

                all_capabilities.append(finalized)

            capability_by_identity = {}

            for capability in finalized_capabilities:
                key = (
                    capability["capability_id"],
                    capability["indian_standard_no"],
                    capability["product"],
                    capability["designation"]
                )

                capability_by_identity[key] = capability

            for test in tests:
                matching = None

                for capability in finalized_capabilities:
                    if (
                        capability["indian_standard_no"]
                        == test["indian_standard_no"]
                        and
                        capability["product"]
                        == test["product"]
                        and
                        capability["designation"]
                        == test["designation"]
                    ):
                        matching = capability
                        break

                if matching is not None:
                    all_tests.append(
                        finalize_test(
                            test,
                            matching,
                            lab,
                            raw_file,
                            timestamp
                        )
                    )

            all_labs.append({
                "lab_code": clean(lab.get("lab_code")),
                "lab_name": clean(lab.get("lab_name")),
                "scope_id": sid,
                "scope_url": clean(lab.get("scope_url")),
                "raw_file": str(
                    raw_file.relative_to(BASE_DIR)
                ).replace("\\", "/"),
                "source": "BIS_LIMS",
                "retrieved_at": timestamp,
                "capability_count": len(capabilities),
                "test_count": len(tests)
            })

            manifest.append({
                "scope_id": sid,
                "lab_code": clean(lab.get("lab_code")),
                "lab_name": clean(lab.get("lab_name")),
                "scope_url": clean(lab.get("scope_url")),
                "raw_file": str(
                    raw_file.relative_to(BASE_DIR)
                ).replace("\\", "/"),
                "status": "success",
                "capabilities": len(capabilities),
                "tests": len(tests)
            })

        except Exception as e:
            stats["parse_errors"] += 1

            manifest.append({
                "scope_id": sid,
                "lab_code": clean(lab.get("lab_code")),
                "lab_name": clean(lab.get("lab_name")),
                "scope_url": clean(lab.get("scope_url")),
                "status": "error",
                "error": repr(e)
            })

        if index % 25 == 0:
            print(
                f"Processed {index}/{len(labs)} labs..."
            )

    capability_seen = set()
    unique_capabilities = []

    for capability in all_capabilities:
        key = (
            capability["scope_id"],
            norm(capability["indian_standard_no"]),
            norm(capability["product"]),
            norm(capability["designation"])
        )

        if key in capability_seen:
            continue

        capability_seen.add(key)
        unique_capabilities.append(capability)

    test_seen = set()
    unique_tests = []

    for test in all_tests:
        key = (
            test["scope_id"],
            test["capability_id"],
            norm(test["clause_raw"]),
            norm(test["exclusion"]),
            test["testing_charge_raw"],
            norm(test["effective_date"]),
            norm(test["remark"])
        )

        if key in test_seen:
            continue

        test_seen.add(key)
        unique_tests.append(test)

    with open(OUT_LABS, "w", encoding="utf-8") as f:
        json.dump(
            all_labs,
            f,
            indent=2,
            ensure_ascii=False
        )

    with open(OUT_CAPABILITIES, "w", encoding="utf-8") as f:
        json.dump(
            unique_capabilities,
            f,
            indent=2,
            ensure_ascii=False
        )

    with open(OUT_TESTS, "w", encoding="utf-8") as f:
        json.dump(
            unique_tests,
            f,
            indent=2,
            ensure_ascii=False
        )

    normalized_manifest = {
        "source": "BIS_LIMS",
        "version": "4.0",
        "generated_at": timestamp,
        "statistics": {
            **stats,
            "capabilities": len(unique_capabilities),
            "tests": len(unique_tests)
        },
        "labs": manifest
    }

    with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(
            normalized_manifest,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print("BIS LIMS NORMALIZATION COMPLETE")
    print("=" * 70)
    print(f"Labs:                  {len(all_labs):,}")
    print(f"Labs with HTML:        {stats['labs_with_html']:,}")
    print(f"Labs without HTML:     {stats['labs_without_html']:,}")
    print(f"Capability tables:     {stats['capability_tables']:,}")
    print(f"Capabilities:          {len(unique_capabilities):,}")
    print(f"Test tables:           {stats['test_tables']:,}")
    print(f"Tests:                 {len(unique_tests):,}")
    print(f"Parse errors:          {stats['parse_errors']:,}")
    print(f"Unique IS numbers:     {len({norm(x['indian_standard_no']) for x in unique_capabilities}):,}")
    print(f"Unique products:       {len({norm(x['product']) for x in unique_capabilities}):,}")
    print("=" * 70)


if __name__ == "__main__":
    main()
