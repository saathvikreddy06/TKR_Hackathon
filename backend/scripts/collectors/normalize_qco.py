import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "qco" / "notifications"
MANIFEST = ROOT / "data" / "manifests" / "bis_qco_notifications_manifest.json"
OUT_DIR = ROOT / "data" / "normalized" / "qco"

OUT_DIR.mkdir(parents=True, exist_ok=True)

DOCUMENT_TYPES = [
    ("QCO_RESIND", [
        r"\brescind(?:ing|ed)?\b",
        r"\brescission\b",
        r"\bwithdraw(?:al|n|s|ing)?\b"
    ]),
    ("QCO_CORRIGENDUM", [
        r"\bcorrigendum\b",
        r"\bcorrection\b"
    ]),
    ("QCO_DEFERMENT", [
        r"\bdefer(?:ment|red)?\b",
        r"\bdeferment\b"
    ]),
    ("QCO_EXTENSION", [
        r"\bextension\b",
        r"\bextended\b",
        r"\bextend(?:ed|ing)?\b"
    ]),
    ("QCO_EXEMPTION", [
        r"\bexemption\b",
        r"\bexempt(?:ed|ion)?\b"
    ]),
    ("QCO_AMENDMENT", [
        r"\bamend(?:ment|ed|ing)?\b",
        r"\bsecond amendment\b",
        r"\bfirst amendment\b"
    ]),
    ("CRO_CRS", [
        r"\bcompulsory registration order\b",
        r"\bCRO\b",
        r"\bCRS\b",
        r"electronics and information technology goods"
    ]),
    ("QCO_WITHDRAWAL", [
        r"\bwithdrawal\b"
    ]),
    ("QCO", [
        r"\bquality control order\b",
        r"\bquality control order,?\s*\d{4}\b",
        r"\bQCO\b"
    ])
]

IS_PATTERNS = [
    re.compile(r"\bIS\s*[:\-]?\s*(\d{3,6}(?:\s*[-/]\s*\d{1,3})?(?:\s*Part\s*\d+)?)\b", re.I),
    re.compile(r"\bIS\s+(\d{3,6}(?:[-/]\d{1,3})?)\b", re.I),
    re.compile(r"\bIS\/IEC\s+(\d{3,6}(?:[-/]\d{1,3})?)\b", re.I),
    re.compile(r"\bIEC\s+(\d{3,6}(?:[-/]\d{1,3})?)\b", re.I)
]

DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{4})\b"),
    re.compile(r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b", re.I),
    re.compile(r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b", re.I)
]

ORDER_PATTERNS = [
    re.compile(r"\bS\.?\s*O\.?\s*[\s./-]*(\d{2,8})\s*[\s./-]*E?\b", re.I),
    re.compile(r"\bG\.?\s*S\.?\s*R\.?\s*[\s./-]*(\d{2,8})\b", re.I),
    re.compile(r"\bF\.?\s*No\.?\s*[:\-]?\s*([A-Z0-9./()\-]+)\b", re.I)
]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def classify(text):
    sample = text[:30000].lower()

    for document_type, patterns in DOCUMENT_TYPES:
        for pattern in patterns:
            if re.search(pattern, sample, re.I):
                return document_type

    return "UNKNOWN"


def extract_is_numbers(text):
    values = set()

    for pattern in IS_PATTERNS:
        for match in pattern.findall(text):
            value = match if isinstance(match, str) else match[0]
            value = re.sub(r"\s+", " ", value.strip())
            value = value.replace(" ", "")
            if len(value) >= 3:
                values.add(value)

    return sorted(values)


def extract_dates(text):
    values = set()

    for pattern in DATE_PATTERNS:
        for match in pattern.findall(text):
            values.add(match.strip())

    return sorted(values)


def extract_orders(text):
    values = set()

    for pattern in ORDER_PATTERNS:
        for match in pattern.findall(text):
            value = match.strip()
            if value:
                values.add(value)

    return sorted(values)


def infer_title(pages, filename):
    text = "\n".join(pages[:3])

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines[:80]:
        lower = line.lower()

        if (
            "quality control order" in lower
            or "compulsory registration order" in lower
            or "electronics and information technology goods" in lower
            or "technical regulation" in lower
        ):
            return line[:500]

    return Path(filename).stem.replace("_", " ")


def infer_scheme(text):
    lower = text[:30000].lower()

    if "scheme x" in lower:
        return "SCHEME_X"
    if "scheme iv" in lower:
        return "SCHEME_IV"
    if "scheme ii" in lower:
        return "SCHEME_II"
    if "scheme i" in lower:
        return "SCHEME_I"

    return None


def text_quality(pages):
    if not pages:
        return "NO_TEXT"

    combined = " ".join(pages)
    chars = len(combined)
    alnum = sum(c.isalnum() for c in combined)

    if chars < 200:
        return "VERY_LOW"

    ratio = alnum / max(chars, 1)

    if ratio < 0.2:
        return "LOW"

    if chars < 1000:
        return "MEDIUM"

    return "GOOD"


def canonical_documents(files):
    groups = defaultdict(list)

    for path in files:
        digest = sha256(path)
        groups[digest].append(path)

    result = []

    for digest, paths in sorted(groups.items()):
        paths.sort(key=lambda p: p.name)
        result.append((digest, paths[0], paths))

    return result


def main():
    files = sorted(RAW_DIR.glob("*.pdf"))

    if not files:
        raise SystemExit(f"No PDFs found in {RAW_DIR}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_documents = manifest.get("documents", [])

    manifest_by_file = {
        Path(d.get("raw_file", "")).name: d
        for d in manifest_documents
    }

    groups = canonical_documents(files)

    documents = []
    pages_output = []
    failures = []
    duplicate_groups = []

    for index, (digest, canonical, duplicates) in enumerate(groups, start=1):
        print(f"[{index}/{len(groups)}] {canonical.name}")

        if len(duplicates) > 1:
            duplicate_groups.append({
                "sha256": digest,
                "canonical_file": canonical.name,
                "duplicate_files": [p.name for p in duplicates]
            })

        try:
            reader = PdfReader(str(canonical))
            page_texts = []

            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    text = clean_text(page.extract_text() or "")
                except Exception:
                    text = ""

                page_texts.append(text)

                pages_output.append({
                    "document_id": f"QCO_{digest[:16]}",
                    "page_number": page_number,
                    "text": text
                })

            combined = "\n".join(page_texts)
            document_type = classify(combined)
            is_numbers = extract_is_numbers(combined)
            dates = extract_dates(combined)
            orders = extract_orders(combined)
            source_metadata = manifest_by_file.get(canonical.name, {})

            document = {
                "document_id": f"QCO_{digest[:16]}",
                "document_type": document_type,
                "title": infer_title(page_texts, canonical.name),
                "order_numbers": orders,
                "dates_found": dates,
                "is_numbers": is_numbers,
                "scheme": infer_scheme(combined),
                "source_url": source_metadata.get("url"),
                "final_url": source_metadata.get("final_url"),
                "raw_file": str(canonical.relative_to(ROOT.parent.parent)),
                "sha256": digest,
                "page_count": len(reader.pages),
                "text_quality": text_quality(page_texts),
                "text_characters": len(combined),
                "status": "PROCESSED",
                "retrieved_at": source_metadata.get("retrieved_at"),
                "normalized_at": datetime.now(timezone.utc).isoformat()
            }

            documents.append(document)

        except Exception as exc:
            failures.append({
                "file": canonical.name,
                "sha256": digest,
                "error": str(exc)
            })

    relationships = []

    for document in documents:
        for duplicate in duplicate_groups:
            if duplicate["sha256"] == document["sha256"]:
                for filename in duplicate["duplicate_files"]:
                    if filename != duplicate["canonical_file"]:
                        relationships.append({
                            "relationship_type": "DUPLICATE_CONTENT",
                            "document_id": document["document_id"],
                            "duplicate_file": filename
                        })

    (OUT_DIR / "qco_documents.json").write_text(
        json.dumps(documents, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    (OUT_DIR / "qco_pages.json").write_text(
        json.dumps(pages_output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    (OUT_DIR / "qco_relationships.json").write_text(
        json.dumps(relationships, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    (OUT_DIR / "qco_duplicates.json").write_text(
        json.dumps(duplicate_groups, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    (OUT_DIR / "qco_failures.json").write_text(
        json.dumps(failures, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    manifest_output = {
        "source": "BIS QCO",
        "normalized_at": datetime.now(timezone.utc).isoformat(),
        "raw_pdf_files": len(files),
        "unique_documents": len(documents),
        "duplicate_groups": len(duplicate_groups),
        "duplicate_files": sum(
            len(group["duplicate_files"]) - 1
            for group in duplicate_groups
        ),
        "failed_documents": len(failures),
        "document_types": dict(
            sorted(
                {
                    t: sum(1 for d in documents if d["document_type"] == t)
                    for t in sorted(set(d["document_type"] for d in documents))
                }.items()
            )
        ),
        "documents_with_is": sum(bool(d["is_numbers"]) for d in documents),
        "pages": len(pages_output)
    }

    (OUT_DIR / "qco_normalized_manifest.json").write_text(
        json.dumps(manifest_output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print()
    print("BIS QCO NORMALIZATION")
    print(f"Raw PDFs:              {len(files)}")
    print(f"Unique documents:      {len(documents)}")
    print(f"Duplicate groups:      {len(duplicate_groups)}")
    print(f"Duplicate files:       {manifest_output['duplicate_files']}")
    print(f"Pages:                 {len(pages_output)}")
    print(f"Documents with IS:     {manifest_output['documents_with_is']}")
    print(f"Failed documents:      {len(failures)}")
    print()
    print("Document types:")

    for key, value in manifest_output["document_types"].items():
        print(f"  {key:<24} {value}")

    print()
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
