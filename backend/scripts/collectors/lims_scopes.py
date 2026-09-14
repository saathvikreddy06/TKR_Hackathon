import json
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT = BASE_DIR / "data" / "normalized" / "labs" / "bis_lims_recognized_labs.json"
RAW_DIR = BASE_DIR / "data" / "raw" / "labs" / "scopes"
OUTPUT = BASE_DIR / "data" / "normalized" / "labs" / "bis_lims_recognized_lab_scopes.json"
MANIFEST = BASE_DIR / "data" / "manifests" / "bis_lims_scopes_manifest.json"

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
MANIFEST.parent.mkdir(parents=True, exist_ok=True)


def load_labs():
    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = data.get("laboratories") or data.get("labs") or data.get("data")

    if not isinstance(data, list):
        raise ValueError("Could not find laboratory records")

    return data


def scope_id(url):
    parts = urlparse(url).path.rstrip("/").split("/")
    return parts[-1] if parts else ""


def clean(value):
    return " ".join(str(value or "").split())


def parse_tables(html):
    soup = BeautifulSoup(html, "html.parser")
    tables = []

    for table in soup.find_all("table"):
        rows = []

        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"], recursive=False)

            if not cells:
                continue

            row = [clean(cell.get_text(" ", strip=True)) for cell in cells]

            if any(row):
                rows.append(row)

        if rows:
            tables.append(rows)

    return tables


def fetch(session, url, retries=4):
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def main():
    labs = load_labs()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })

    results = []
    manifest = []

    success = 0
    failed = 0

    print("=" * 70)
    print("BIS LIMS SCOPE COLLECTION")
    print("=" * 70)

    for index, lab in enumerate(labs, 1):
        url = str(lab.get("scope_url", "")).strip()
        sid = scope_id(url)

        if not url or not sid:
            failed += 1
            continue

        raw_file = RAW_DIR / f"{sid}.html"

        try:
            content = fetch(session, url)

            raw_file.write_text(
                content,
                encoding="utf-8"
            )

            tables = parse_tables(content)

            record = {
                "lab_code": clean(lab.get("lab_code")),
                "lab_name": clean(lab.get("lab_name")),
                "scope_url": url,
                "scope_id": sid,
                "tables": tables,
                "retrieved_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime()
                ),
                "raw_file": str(
                    raw_file.relative_to(BASE_DIR)
                ).replace("\\", "/")
            }

            results.append(record)

            manifest.append({
                "scope_id": sid,
                "lab_code": clean(lab.get("lab_code")),
                "lab_name": clean(lab.get("lab_name")),
                "scope_url": url,
                "raw_file": str(
                    raw_file.relative_to(BASE_DIR)
                ).replace("\\", "/"),
                "status": "success"
            })

            success += 1

        except Exception as e:
            failed += 1

            manifest.append({
                "scope_id": sid,
                "lab_code": clean(lab.get("lab_code")),
                "lab_name": clean(lab.get("lab_name")),
                "scope_url": url,
                "status": "failed",
                "error": repr(e)
            })

        if index % 25 == 0:
            print(
                f"Processed {index}/{len(labs)} "
                f"| Success: {success} | Failed: {failed}"
            )

        time.sleep(1.5)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            {
                "laboratories": results
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": "BIS_LIMS",
                "total": len(labs),
                "success": success,
                "failed": failed,
                "records": manifest
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)
    print(f"Labs:              {len(labs)}")
    print(f"Successful:        {success}")
    print(f"Failed:            {failed}")
    print(f"Unique HTML files: {len(list(RAW_DIR.glob('*.html')))}")
    print("=" * 70)


if __name__ == "__main__":
    main()

