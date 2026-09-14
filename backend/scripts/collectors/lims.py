import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://lims.bis.gov.in"
LABS_URL = f"{BASE_URL}/home/labs/"

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

RAW_DIR = DATA_DIR / "raw" / "labs"
NORMALIZED_DIR = DATA_DIR / "normalized" / "labs"
MANIFEST_DIR = DATA_DIR / "manifests"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

REQUEST_DELAY_SECONDS = 0.5


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def fetch_page(session: requests.Session, url: str) -> str:
    response = session.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


def get_total_pages(html: str) -> int:
    """
    BIS currently displays 20 laboratories per page.

    We detect the 'Last' pagination link rather than hardcoding
    the current number of pages.
    """
    soup = BeautifulSoup(html, "html.parser")

    last_link = None

    for link in soup.find_all("a", href=True):
        text = clean_text(link.get_text(" ", strip=True)).lower()

        if text == "last":
            last_link = link
            break

    if last_link:
        href = last_link.get("href", "")

        match = re.search(
            r"[?&]page=(\d+)",
            href,
        )

        if match:
            return int(match.group(1))

    # Fallback: inspect pagination links.
    pages = []

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")

        match = re.search(
            r"[?&]page=(\d+)",
            href,
        )

        if match:
            pages.append(int(match.group(1)))

    return max(pages, default=1)


def parse_laboratories(
    html: str,
    page_number: int,
) -> list[dict]:

    soup = BeautifulSoup(html, "html.parser")

    laboratories = []

    for table in soup.find_all("table"):

        rows = table.find_all("tr")

        if not rows:
            continue

        header_row = rows[0]

        headers = [
            clean_text(
                cell.get_text(" ", strip=True)
            ).lower()
            for cell in header_row.find_all(
                ["th", "td"]
            )
        ]

        header_text = " ".join(headers)

        if "lab code" not in header_text:
            continue

        if "lab name" not in header_text:
            continue

        for row in rows[1:]:

            cells = row.find_all(
                ["td", "th"]
            )

            if len(cells) < 8:
                continue

            values = [
                clean_text(
                    cell.get_text(" ", strip=True)
                )
                for cell in cells
            ]

            # Expected BIS structure:
            #
            # S.No.
            # Lab Code
            # Lab Name
            # Address
            # Contact Person
            # Contact Number
            # Email
            # Validity Date
            # View Scope

            lab_code = values[1]
            lab_name = values[2]
            address = values[3]
            contact_person = values[4]
            contact_number = values[5]
            email = values[6]
            validity_date = values[7]

            scope_url = None

            for link in row.find_all(
                "a",
                href=True,
            ):
                text = clean_text(
                    link.get_text(
                        " ",
                        strip=True,
                    )
                ).lower()

                if "view scope" in text:
                    scope_url = urljoin(
                        BASE_URL,
                        link["href"],
                    )
                    break

            laboratories.append(
                {
                    "source": "BIS_LIMS",
                    "page": page_number,
                    "lab_code": lab_code,
                    "lab_name": lab_name,
                    "address": address,
                    "contact_person": contact_person,
                    "contact_number": contact_number,
                    "email": email,
                    "validity_date": validity_date,
                    "scope_url": scope_url,
                    "source_url": (
                        f"{LABS_URL}?page={page_number}"
                        if page_number > 1
                        else LABS_URL
                    ),
                }
            )

    return laboratories


def save_raw(
    html: str,
    page_number: int,
) -> Path:

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        "bis_lims_labs_page_"
        f"{page_number}.html"
    )

    path = RAW_DIR / filename

    path.write_text(
        html,
        encoding="utf-8",
    )

    return path


def save_json(
    data,
    path: Path,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def create_manifest(
    raw_pages: list[dict],
    record_count: int,
):

    MANIFEST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    page_hashes = []

    for page in raw_pages:

        content = Path(
            page["path"]
        ).read_text(
            encoding="utf-8"
        )

        page_hashes.append(
            {
                "page": page["page"],
                "path": page["path"],
                "sha256": sha256_text(content),
            }
        )

    manifest = {
        "document_id": "BIS_LIMS_RECOGNIZED_LABS",
        "source_id": "bis_lims",
        "source_url": LABS_URL,
        "source_type": "BIS_OFFICIAL",
        "document_type": "LABORATORIES",
        "lab_category": "RECOGNIZED",
        "retrieved_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "status": "downloaded",
        "record_count": record_count,
        "page_count": len(raw_pages),
        "parser_version": "2.0",
        "pages": page_hashes,
    }

    save_json(
        manifest,
        MANIFEST_DIR
        / "bis_lims_manifest.json",
    )


def main():

    print()
    print("=" * 60)
    print("BIS LIMS LABORATORY COLLECTOR")
    print("=" * 60)
    print()

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    NORMALIZED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with requests.Session() as session:

        print(
            f"Fetching first page: {LABS_URL}"
        )

        first_html = fetch_page(
            session,
            LABS_URL,
        )

        total_pages = get_total_pages(
            first_html
        )

        print(
            f"Detected pages: {total_pages}"
        )

        all_laboratories = []

        raw_pages = []

        # Process first page.
        first_path = save_raw(
            first_html,
            1,
        )

        first_labs = parse_laboratories(
            first_html,
            1,
        )

        all_laboratories.extend(
            first_labs
        )

        raw_pages.append(
            {
                "page": 1,
                "path": str(first_path),
            }
        )

        print(
            f"Page 1: {len(first_labs)} labs"
        )

        # Process remaining pages.
        for page_number in range(
            2,
            total_pages + 1,
        ):

            url = (
                f"{LABS_URL}"
                f"?page={page_number}"
            )

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

            print(
                f"Fetching page "
                f"{page_number}/{total_pages}..."
            )

            try:

                html = fetch_page(
                    session,
                    url,
                )

                path = save_raw(
                    html,
                    page_number,
                )

                labs = parse_laboratories(
                    html,
                    page_number,
                )

                all_laboratories.extend(
                    labs
                )

                raw_pages.append(
                    {
                        "page": page_number,
                        "path": str(path),
                    }
                )

                print(
                    f"  Found {len(labs)} labs"
                )

            except Exception as exc:

                print(
                    f"  ERROR on page "
                    f"{page_number}: {exc}"
                )

    # Deduplicate by lab code.
    unique_labs = {}

    for lab in all_laboratories:

        lab_code = lab["lab_code"]

        if lab_code:
            unique_labs[lab_code] = lab

    laboratories = list(
        unique_labs.values()
    )

    normalized = {
        "source": {
            "source_id": "bis_lims",
            "source_name": (
                "BIS Laboratory "
                "Information Management System"
            ),
            "source_url": LABS_URL,
            "category": "RECOGNIZED",
            "retrieved_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        },
        "statistics": {
            "pages": total_pages,
            "records_collected": (
                len(all_laboratories)
            ),
            "unique_laboratories": (
                len(laboratories)
            ),
        },
        "laboratories": laboratories,
    }

    normalized_path = (
        NORMALIZED_DIR
        / "bis_lims_recognized_labs.json"
    )

    save_json(
        normalized,
        normalized_path,
    )

    create_manifest(
        raw_pages,
        len(laboratories),
    )

    print()
    print("=" * 60)
    print("COLLECTION COMPLETE")
    print("=" * 60)
    print(
        f"Pages: {total_pages}"
    )
    print(
        "Records collected: "
        f"{len(all_laboratories)}"
    )
    print(
        "Unique laboratories: "
        f"{len(laboratories)}"
    )
    print(
        f"Normalized: {normalized_path}"
    )
    print()


if __name__ == "__main__":
    main()