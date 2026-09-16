import json
import re
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

MASTER = DATA / "normalized/standards/bis_standards_master.json"
DETAILS = DATA / "normalized/standards/bis_standards_details.json"
LAB_TESTS = DATA / "normalized/labs/bis_lims_tests.json"
QCO_LINKS = DATA / "normalized/standards/standard_qco_links.json"
QCO_STATE = DATA / "normalized/qco/qco_regulatory_state.json"

OUTPUT = DATA / "processed/knowledge_documents.json"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def canonical_is(value):
    value = clean(value).upper()
    value = value.replace("INDIAN STANDARD", "IS")
    value = re.sub(r"[:\-]\s*\d{4}", "", value)
    value = re.sub(r"\(\s*\d{4}\s*\)", "", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*/\s*", "/", value)
    value = re.sub(r"\s*\(\s*", " (", value)
    value = re.sub(r"\s*\)\s*", ")", value)
    return value.strip()


def is_family(value):
    value = canonical_is(value)
    match = re.match(r"(IS\s+\d+)", value)
    return match.group(1) if match else value


def main():
    master = load(MASTER)
    details = load(DETAILS)
    lab_tests = load(LAB_TESTS)
    qco_links = load(QCO_LINKS)
    qco_state = load(QCO_STATE)

    standards = master.get("standards", [])

    detail_map = {}

    if isinstance(details, dict):
        for key, value in details.items():
            if isinstance(value, dict):
                sid = clean(value.get("standard_id") or key)
                if sid:
                    detail_map[sid] = value

    tests_by_is = defaultdict(list)

    if isinstance(lab_tests, list):
        for row in lab_tests:
            is_no = canonical_is(row.get("indian_standard_no"))
            if is_no:
                tests_by_is[is_no].append(row)

    tests_by_family = defaultdict(list)

    for is_no, rows in tests_by_is.items():
        tests_by_family[is_family(is_no)].extend(rows)

    qco_by_family = defaultdict(list)

    for link in qco_links.get("links", []):
        matched = link.get("matched_is_numbers", [])

        if not matched:
            matched = [link.get("standard_number", "")]

        for value in matched:
            family = is_family(value)
            if family:
                qco_by_family[family].append(link)

    state_by_family = {}

    states = qco_state.get("states", {})

    if isinstance(states, dict):
        for key, value in states.items():
            state_by_family[is_family(key)] = value

    documents = []
    represented_qcos = set()

    for standard in standards:
        sid = clean(standard.get("standard_id"))
        number = clean(standard.get("standard_number"))
        title = clean(standard.get("title"))

        if not sid and not number:
            continue

        canonical = canonical_is(number)
        family = is_family(number)

        detail = detail_map.get(sid, {})

        text = [
            f"Indian Standard: {number}",
            f"Title: {title}"
        ]

        for field, label in [
            ("department", "Department"),
            ("sectional_committee", "Sectional Committee"),
            ("type", "Type"),
            ("published_on", "Published On")
        ]:
            value = clean(standard.get(field))
            if value:
                text.append(f"{label}: {value}")

        details_list = detail.get("details", [])

        if isinstance(details_list, list):
            for item in details_list:
                if isinstance(item, dict):
                    name = clean(item.get("standardName"))
                    if name:
                        text.append(f"Standard Name: {name}")

        documents.append({
            "document_id": f"standard_{sid or canonical}",
            "document_type": "standard",
            "standard_id": sid,
            "standard_number": number,
            "title": title,
            "text": "\n".join(text),
            "source": "BIS",
            "source_url": "https://www.bis.gov.in/know-your-standard/?lang=en"
        })

        rows = tests_by_is.get(canonical, [])

        if not rows:
            rows = tests_by_family.get(family, [])

            rows = [
                row for row in rows
                if is_family(row.get("indian_standard_no")) == family
            ]

        grouped = defaultdict(list)

        for row in rows:
            lab = clean(row.get("lab_name"))
            product = clean(row.get("product"))
            grouped[(lab, product)].append(row)

        for index, ((lab, product), group) in enumerate(
            grouped.items(), 1
        ):
            seen_tests = set()
            lines = [
                f"Indian Standard: {number}",
                f"Product: {product}",
                f"Laboratory: {lab}"
            ]

            lab_code = clean(group[0].get("lab_code"))

            if lab_code:
                lines.append(f"Lab Code: {lab_code}")

            lines.append("Testing scope:")

            for row in group:
                clause = clean(row.get("clause_raw"))
                designation = clean(row.get("designation"))
                exclusion = clean(row.get("exclusion"))
                charge = row.get("testing_charge")

                key = (
                    clause,
                    designation,
                    exclusion,
                    str(charge)
                )

                if key in seen_tests:
                    continue

                seen_tests.add(key)

                line = clause

                if designation:
                    line += f" | Designation: {designation}"

                if exclusion:
                    line += f" | Exclusion: {exclusion}"

                if charge is not None:
                    line += f" | Testing charge: {charge}"

                if line.strip():
                    lines.append(f"- {line}")

            documents.append({
                "document_id": f"testing_{sid or canonical}_{index}",
                "document_type": "standard_testing",
                "standard_id": sid,
                "standard_number": number,
                "title": title,
                "product": product,
                "lab_name": lab,
                "lab_code": lab_code,
                "test_count": len(seen_tests),
                "text": "\n".join(lines),
                "source": "BIS LIMS",
                "source_url": clean(group[0].get("scope_url"))
            })

        qcos = qco_by_family.get(family, [])

        if qcos:
            lines = [
                f"Indian Standard: {number}",
                f"Title: {title}",
                "BIS QCO/regulatory references:"
            ]

            seen = set()

            for qco in qcos:
                qid = clean(qco.get("qco_document_id"))
                relationship = clean(qco.get("relationship"))
                evidence = clean(qco.get("evidence"))
                order = clean(qco.get("order_number"))
                date = clean(qco.get("order_date"))

                key = (qid, relationship, evidence)

                if key in seen:
                    continue

                seen.add(key)

                lines.append(f"Relationship: {relationship}")
                lines.append(f"QCO Document: {qid}")

                if order:
                    lines.append(f"Order Number: {order}")

                if date:
                    lines.append(f"Order Date: {date}")

                if evidence:
                    lines.append(f"Evidence: {evidence}")

                if qid:
                    represented_qcos.add(qid)

            state = state_by_family.get(family)

            if state:
                lines.append(
                    "Regulatory state data: "
                    + json.dumps(state, ensure_ascii=False)
                )

            documents.append({
                "document_id": f"qco_{sid or family}",
                "document_type": "standard_qco",
                "standard_id": sid,
                "standard_number": number,
                "title": title,
                "text": "\n".join(lines),
                "source": "BIS QCO",
                "source_url": "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/?lang=en"
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "documents": documents
    }

    temp = OUTPUT.with_suffix(".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    temp.replace(OUTPUT)

    counts = defaultdict(int)

    for document in documents:
        counts[document["document_type"]] += 1

    print(f"Documents: {len(documents)}")

    for key, value in sorted(counts.items()):
        print(f"{key}: {value}")

    print(f"QCO documents represented: {len(represented_qcos)}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
