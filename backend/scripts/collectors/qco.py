import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "qco"
PAGES = RAW / "pages"
NOTIFICATIONS = RAW / "notifications"
MANIFEST = ROOT / "data" / "manifests" / "bis_qco_manifest.json"
NOTIFICATION_MANIFEST = ROOT / "data" / "manifests" / "bis_qco_notifications_manifest.json"

HEADERS = {
    "User-Agent": "StandIQ-BIS-DataCollector/1.0"
}

SOURCES = {
    "scheme_i": "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-i-mark-scheme/?lang=en",
    "scheme_ii": "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-ii-registration-scheme/?lang=en",
    "scheme_iv": "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-4/?lang=en",
    "scheme_x": "https://www.bis.gov.in/products-under-compulsory-certification-scheme-x/?lang=en",
    "upcoming": "https://www.bis.gov.in/upcoming-qcos-notified-and-due-for-implementation/?lang=en"
}

PDF_EXTENSIONS = (".pdf",)

RELEVANCE_TERMS = (
    "qco",
    "quality control order",
    "notification",
    "gazette",
    "order",
    "amendment",
    "amending",
    "supersed",
    "extension",
    "exemption",
    "corrigendum",
    "withdraw",
    "implementation"
)


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def is_bis_url(url):
    host = urlparse(url).netloc.lower()
    return host == "bis.gov.in" or host.endswith(".bis.gov.in")


def is_relevant_notification(text, url):
    value = f"{text} {url}".lower()

    if not is_bis_url(url):
        return False

    if not url.lower().split("?")[0].endswith(PDF_EXTENSIONS):
        return False

    return any(term in value for term in RELEVANCE_TERMS)


def safe_filename(index, url):
    path = urlparse(url).path
    name = Path(path).name

    if not name:
        name = f"notification_{index}.pdf"

    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)

    if not name.lower().endswith(".pdf"):
        name += ".pdf"

    return f"{index:05d}_{name}"


def fetch(url, attempts=4):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url,
                headers={
                    **HEADERS,
                    "Connection": "close"
                },
                timeout=(15, 120)
            )
            response.raise_for_status()

            content = response.content
            expected = response.headers.get("Content-Length")

            if expected and len(content) != int(expected):
                raise requests.exceptions.ChunkedEncodingError(
                    f"Incomplete response: {len(content)} of {expected} bytes"
                )

            return (
                content,
                response.url,
                response.headers.get("content-type", "")
            )

        except Exception as exc:
            last_error = exc

            if attempt < attempts:
                import time
                time.sleep(attempt * 3)

    raise last_error

def extract_page_records(html, source_name, url):
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for table_index, table in enumerate(soup.find_all("table")):
        headers = [
            clean(th.get_text(" ", strip=True)).lower()
            for th in table.find_all("th")
        ]

        for row_index, row in enumerate(table.find_all("tr")):
            cells = row.find_all(["td", "th"])
            values = [clean(cell.get_text(" ", strip=True)) for cell in cells]

            if not values or all(not value for value in values):
                continue

            links = []

            for link in row.find_all("a", href=True):
                text = clean(link.get_text(" ", strip=True))
                href = urljoin(url, link["href"])

                links.append({
                    "text": text,
                    "url": href,
                    "is_notification_candidate": is_relevant_notification(
                        text,
                        href
                    )
                })

            records.append({
                "source": source_name,
                "source_url": url,
                "table_index": table_index,
                "row_index": row_index,
                "headers": headers,
                "values": values,
                "links": links
            })

    return records


def collect_pages(retrieved_at):
    pages = []
    records = []

    for name, url in SOURCES.items():
        print(f"Fetching {name}...")

        try:
            content, final_url, content_type = fetch(url)

            page_path = PAGES / f"{name}.html"
            page_path.write_bytes(content)

            page_records = extract_page_records(
                content,
                name,
                final_url
            )

            pages.append({
                "source_name": name,
                "url": final_url,
                "raw_file": str(page_path.relative_to(ROOT)),
                "content_type": content_type or "text/html",
                "sha256": sha256(content),
                "record_count": len(page_records),
                "retrieved_at": retrieved_at,
                "status": "success"
            })

            records.extend(page_records)

            print(f"  Records: {len(page_records)}")

        except Exception as exc:
            pages.append({
                "source_name": name,
                "url": url,
                "retrieved_at": retrieved_at,
                "status": "failed",
                "error": str(exc)
            })

            print(f"  FAILED: {exc}")

    return pages, records


def discover_notifications(records):
    discovered = {}

    for record in records:
        for link in record.get("links", []):
            if not link.get("is_notification_candidate"):
                continue

            url = link["url"]

            if url not in discovered:
                discovered[url] = {
                    "url": url,
                    "link_texts": [],
                    "sources": [],
                    "source_urls": []
                }

            if link["text"] not in discovered[url]["link_texts"]:
                discovered[url]["link_texts"].append(link["text"])

            if record["source"] not in discovered[url]["sources"]:
                discovered[url]["sources"].append(record["source"])

            if record["source_url"] not in discovered[url]["source_urls"]:
                discovered[url]["source_urls"].append(record["source_url"])

    return list(discovered.values())


def download_notifications(discovered, retrieved_at):
    NOTIFICATIONS.mkdir(parents=True, exist_ok=True)

    results = []

    for index, item in enumerate(discovered, start=1):
        url = item["url"]
        filename = safe_filename(index, url)
        path = NOTIFICATIONS / filename

        print(f"Downloading {index}/{len(discovered)}: {url}")

        try:
            content, final_url, content_type = fetch(url)

            if not content.startswith(b"%PDF"):
                raise ValueError(
                    f"Downloaded content is not a PDF: {content_type}"
                )

            path.write_bytes(content)

            results.append({
                **item,
                "final_url": final_url,
                "raw_file": str(path.relative_to(ROOT)),
                "content_type": content_type,
                "size_bytes": len(content),
                "sha256": sha256(content),
                "retrieved_at": retrieved_at,
                "status": "downloaded"
            })

        except Exception as exc:
            results.append({
                **item,
                "retrieved_at": retrieved_at,
                "status": "failed",
                "error": str(exc)
            })

            print(f"  FAILED: {exc}")

    return results


def main():
    PAGES.mkdir(parents=True, exist_ok=True)
    NOTIFICATIONS.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    retrieved_at = datetime.now(timezone.utc).isoformat()

    pages, records = collect_pages(retrieved_at)

    discovered = discover_notifications(records)

    print()
    print(f"Notification candidates: {len(discovered)}")

    notification_results = download_notifications(
        discovered,
        retrieved_at
    )

    manifest = {
        "source": "BIS",
        "source_type": "BIS_OFFICIAL",
        "retrieved_at": retrieved_at,
        "pages": pages,
        "records": records
    }

    MANIFEST.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    notification_manifest = {
        "source": "BIS",
        "source_type": "BIS_OFFICIAL",
        "retrieved_at": retrieved_at,
        "candidates": len(discovered),
        "downloaded": sum(
            x["status"] == "downloaded"
            for x in notification_results
        ),
        "failed": sum(
            x["status"] == "failed"
            for x in notification_results
        ),
        "documents": notification_results
    }

    NOTIFICATION_MANIFEST.write_text(
        json.dumps(
            notification_manifest,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print("BIS QCO COLLECTION")
    print(f"Pages:                  {len(pages)}")
    print(f"HTML records:           {len(records)}")
    print(f"Notification candidates:{len(discovered)}")
    print(
        "Notification downloads: "
        f"{notification_manifest['downloaded']}"
    )
    print(
        "Notification failures: "
        f"{notification_manifest['failed']}"
    )
    print(f"QCO manifest:            {MANIFEST}")
    print(
        f"Notification manifest:   "
        f"{NOTIFICATION_MANIFEST}"
    )


if __name__ == "__main__":
    main()