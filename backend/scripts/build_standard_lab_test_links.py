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

CAPABILITIES_FILE = (
    DATA / "normalized" / "labs"
    / "bis_lims_capabilities.json"
)

TESTS_FILE = (
    DATA / "normalized" / "labs"
    / "bis_lims_tests.json"
)

LABS_FILE = (
    DATA / "normalized" / "labs"
    / "bis_lims_labs.json"
)

OUTPUT_FILE = (
    DATA / "normalized" / "standards"
    / "standard_lab_test_links.json"
)

AUDIT_FILE = (
    DATA / "manifests"
    / "standard_lab_test_links_manifest.json"
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


def text(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
        )

    return str(value)


def normalize(value):
    value = text(value).upper()
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_is(value):
    value = normalize(value)

    return {
        f"IS {number}"
        for number in re.findall(
            r"\bIS\s*[-:]?\s*(\d{1,6})",
            value,
        )
    }


def get_first(row, keys):
    for key in keys:
        if key in row and row[key] not in (
            None,
            "",
            [],
            {},
        ):
            return row[key]

    return None


def standard_number(row):
    return get_first(
        row,
        [
            "standard_number",
            "standardNumber",
            "indian_standard_no",
            "indianStandardNo",
            "is_number",
            "isNumber",
            "standard_no",
        ],
    )


def lab_code(row):
    return get_first(
        row,
        [
            "lab_code",
            "labCode",
            "lab_id",
            "labId",
        ],
    )


def capability_id(row):
    return get_first(
        row,
        [
            "capability_id",
            "capabilityId",
            "id",
        ],
    )


def test_id(row):
    return get_first(
        row,
        [
            "test_id",
            "testId",
            "id",
        ],
    )


def find_rows(data):
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    for key in (
        "records",
        "data",
        "capabilities",
        "tests",
        "labs",
    ):
        value = data.get(key)

        if isinstance(value, list):
            return value

    return []


def main():
    standards_data = load(STANDARDS_FILE)
    capabilities_data = load(CAPABILITIES_FILE)
    tests_data = load(TESTS_FILE)
    labs_data = load(LABS_FILE)

    standards = standards_data.get(
        "standards",
        [],
    )

    capabilities = find_rows(
        capabilities_data
    )

    tests = find_rows(
        tests_data
    )

    labs = find_rows(
        labs_data
    )

    print("Loaded:")
    print(f"  Standards:    {len(standards)}")
    print(f"  Capabilities: {len(capabilities)}")
    print(f"  Tests:        {len(tests)}")
    print(f"  Labs:         {len(labs)}")
    print()

    standard_index = defaultdict(list)

    for standard in standards:
        if not isinstance(standard, dict):
            continue

        sid = standard.get("standard_id")

        if sid is None:
            continue

        numbers = set()

        numbers |= extract_is(
            standard.get("standard_number")
        )

        for reference in standard.get(
            "lims_references",
            [],
        ):
            numbers |= extract_is(reference)

        for number in numbers:
            standard_index[number].append(
                {
                    "standard_id": str(sid),
                    "standard_number": standard.get(
                        "standard_number"
                    ),
                    "title": standard.get(
                        "title"
                    ),
                }
            )

    lab_index = {}

    for lab in labs:
        if not isinstance(lab, dict):
            continue

        code = lab_code(lab)

        if code is None:
            continue

        lab_index[str(code)] = lab

    capability_index = {}

    for capability in capabilities:
        if not isinstance(capability, dict):
            continue

        cid = capability_id(capability)

        if cid is None:
            continue

        capability_index[str(cid)] = capability

    links = []
    seen = set()

    standards_with_tests = set()
    labs_with_tests = set()
    standards_with_labs = set()

    tests_without_capability = 0
    tests_without_standard = 0

    for index, test in enumerate(tests):
        if not isinstance(test, dict):
            continue

        tid = test_id(test)

        if tid is None:
            tid = f"test-{index}"

        cid = get_first(
            test,
            [
                "capability_id",
                "capabilityId",
                "capability",
            ],
        )

        capability = capability_index.get(
            str(cid)
        ) if cid is not None else None

        if capability is None:
            tests_without_capability += 1

        is_value = get_first(
            test,
            [
                "indian_standard_no",
                "indianStandardNo",
                "standard_number",
                "standardNumber",
                "is_number",
                "isNumber",
            ],
        )

        numbers = extract_is(is_value)

        if not numbers and capability:
            numbers |= extract_is(
                get_first(
                    capability,
                    [
                        "indian_standard_no",
                        "indianStandardNo",
                        "standard_number",
                        "standardNumber",
                        "is_number",
                        "isNumber",
                    ],
                )
            )

        matches = []

        for number in numbers:
            matches.extend(
                standard_index.get(
                    number,
                    [],
                )
            )

        unique_standards = {
            item["standard_id"]: item
            for item in matches
        }

        if not unique_standards:
            tests_without_standard += 1
            continue

        code = lab_code(test)

        if code is None and capability:
            code = lab_code(capability)

        code = (
            str(code)
            if code is not None
            else None
        )

        lab = (
            lab_index.get(code)
            if code is not None
            else None
        )

        for sid, standard in unique_standards.items():
            key = (
                sid,
                code,
                str(cid),
                str(tid),
            )

            if key in seen:
                continue

            seen.add(key)

            record = {
                "standard_id": sid,
                "standard_number": standard[
                    "standard_number"
                ],
                "standard_title": standard[
                    "title"
                ],
                "lab_code": code,
                "lab_name": (
                    get_first(
                        lab,
                        [
                            "lab_name",
                            "labName",
                            "name",
                        ],
                    )
                    if lab
                    else None
                ),
                "capability_id": (
                    str(cid)
                    if cid is not None
                    else None
                ),
                "test_id": str(tid),
                "test_name": get_first(
                    test,
                    [
                        "test_name",
                        "testName",
                        "name",
                        "test",
                    ],
                ),
                "clause": get_first(
                    test,
                    [
                        "clause",
                        "clause_no",
                        "clauseNo",
                        "test_clause",
                    ],
                ),
                "method": get_first(
                    test,
                    [
                        "method",
                        "test_method",
                        "testMethod",
                    ],
                ),
                "product": get_first(
                    test,
                    [
                        "product",
                        "product_name",
                        "productName",
                    ],
                ),
            }

            links.append(record)

            standards_with_tests.add(sid)

            if code:
                labs_with_tests.add(code)
                standards_with_labs.add(sid)

    output = {
        "source": "BIS LIMS",
        "generated_at": now(),
        "standard_count": len(standards),
        "lab_count": len(labs),
        "capability_count": len(capabilities),
        "test_count": len(tests),
        "link_count": len(links),
        "links": links,
    }

    audit = {
        "generated_at": now(),
        "standards": len(standards),
        "labs": len(labs),
        "capabilities": len(capabilities),
        "tests": len(tests),
        "links": len(links),
        "standards_with_tests": len(
            standards_with_tests
        ),
        "standards_with_labs": len(
            standards_with_labs
        ),
        "labs_with_tests": len(
            labs_with_tests
        ),
        "tests_without_capability": (
            tests_without_capability
        ),
        "tests_without_standard": (
            tests_without_standard
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

    print()
    print("=" * 60)
    print("STANDARD ↔ LAB ↔ TEST MAPPING COMPLETE")
    print("=" * 60)
    print(f"Standards:              {len(standards)}")
    print(f"Labs:                   {len(labs)}")
    print(f"Capabilities:           {len(capabilities)}")
    print(f"Tests:                  {len(tests)}")
    print(f"Relationship links:     {len(links)}")
    print(
        f"Standards with tests:   "
        f"{len(standards_with_tests)}"
    )
    print(
        f"Standards with labs:    "
        f"{len(standards_with_labs)}"
    )
    print(
        f"Labs with tests:        "
        f"{len(labs_with_tests)}"
    )
    print(
        f"Tests without standard: "
        f"{tests_without_standard}"
    )
    print(
        f"Tests without capability:"
        f" {tests_without_capability}"
    )
    print()
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
