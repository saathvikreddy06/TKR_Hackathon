import json
from pathlib import Path


DATA_FILE = Path("data/real_bis_standards.json")
OUTPUT_FILE = Path("data/bis_rag_documents.json")


def list_to_text(items):
    """Convert a list into readable bullet-style text."""
    if not items:
        return "Not specified"

    return "\n".join(f"- {item}" for item in items)


def build_rag_text(standard):
    """Convert one BIS standard record into embedding-friendly text."""

    standard_number = standard.get("standard_number", "")
    part = standard.get("part")
    section = standard.get("section")

    identifier = standard_number

    if part:
        identifier += f" {part}"

    if section:
        identifier += f" {section}"

    text = f"""
BIS STANDARD
============

Standard Number:
{identifier}

Standard ID:
{standard.get("standard_id", "")}

Year:
{standard.get("year", "")}

Title:
{standard.get("full_title", "")}

Short Title:
{standard.get("short_title", "")}

Product Category:
{standard.get("product_category", "")}

Industry:
{standard.get("industry", "")}

Certification Scheme:
{standard.get("scheme", "")}

Certification Route:
{standard.get("certification_route", "")}

Mandatory QCO:
{"Yes" if standard.get("mandatory_qco") else "No"}

Status:
{standard.get("status", "")}

Scope:
{standard.get("scope", "")}

Key Testing Parameters:
{list_to_text(standard.get("key_testing_parameters", []))}

Materials:
{list_to_text(standard.get("materials", []))}

Keywords:
{list_to_text(standard.get("keywords", []))}

Publication Date:
{standard.get("publication_date", "")}

Revision Date:
{standard.get("revision_date", "")}

Supersedes:
{standard.get("supersedes") or "None"}

Superseded By:
{standard.get("superseded_by") or "None"}

Amendments:
{list_to_text(standard.get("amendments", []))}

Verification Status:
{standard.get("verification_status", "")}

Verification Note:
{standard.get("verification_note", "")}
""".strip()

    return text


def main():

    print("Loading BIS dataset...")

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        standards = json.load(file)

    print(f"Loaded {len(standards)} standards.")

    documents = []

    for standard in standards:

        document = {
            "standard_id": standard.get("standard_id"),
            "standard_number": standard.get("standard_number"),
            "part": standard.get("part"),
            "section": standard.get("section"),
            "year": standard.get("year"),
            "title": standard.get("full_title"),
            "product_category": standard.get("product_category"),
            "industry": standard.get("industry"),
            "scheme": standard.get("scheme"),
            "mandatory_qco": standard.get("mandatory_qco"),
            "status": standard.get("status"),
            "source_url": standard.get("source_url"),
            "document_url": standard.get("document_url"),
            "text": build_rag_text(standard)
        }

        documents.append(document)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            documents,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(f"Created {len(documents)} RAG documents.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()