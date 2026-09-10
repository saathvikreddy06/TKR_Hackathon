import json


FILE = "data/real_bis_standards.json"


new_standards = [

    {
        "standard_id": "BIS-STD-101",
        "standard_number": "IS 15298",
        "part": "Part 2",
        "section": None,
        "year": "2016",
        "full_title": "Personal Protective Equipment - Part 2: Safety Footwear",
        "short_title": "Safety Footwear",
        "product_category": "Personal Protective Equipment",
        "industry": "Construction, Manufacturing, Industrial Safety",
        "scheme": "Scheme-I (ISI)",
        "certification_route": "Mandatory Scheme-I Certification",
        "mandatory_qco": True,
        "status": "Superseded by IS 15298 (Part 2):2024",
        "publication_date": None,
        "revision_date": "2024",
        "supersedes": None,
        "superseded_by": "IS 15298 (Part 2):2024",
        "amendments": [
            "Amendment No. 1",
            "Amendment No. 2"
        ],
        "scope": (
            "Specifies basic and additional requirements for safety footwear "
            "designed to protect the wearer against workplace hazards. "
            "The standard covers safety footwear with protective features "
            "including toe protection, impact resistance, compression "
            "resistance, slip resistance and puncture protection."
        ),
        "key_testing_parameters": [
            "Toe protection",
            "Impact resistance",
            "Compression resistance",
            "Slip resistance",
            "Penetration resistance",
            "Water resistance",
            "Abrasion resistance",
            "Chromium VI content of leather components"
        ],
        "materials": [
            "Leather and other footwear materials",
            "Protective toe caps",
            "Penetration-resistant inserts"
        ],
        "keywords": [
            "IS 15298",
            "IS 15298 Part 2",
            "IS 15298 (Part 2):2016",
            "safety footwear",
            "safety shoes",
            "protective footwear",
            "industrial safety shoes",
            "200 J toe impact",
            "15 kN compression",
            "PPE footwear"
        ],
        "document_url": (
            "https://www.bis.gov.in/wp-content/uploads/2020/05/"
            "PM-IS-15298-2-cmd2.pdf"
        ),
        "source_url": (
            "https://www.bis.gov.in/product-certification/"
            "products-under-compulsory-certification/"
            "scheme-i-mark-scheme/?lang=en"
        ),
        "source_type": "Official BIS Product Manual / Scheme-I",
        "source_date": "2025-01-10",
        "retrieved_at": "2026-09-10T00:00:00Z",
        "legal_source": {
            "gazette_order": (
                "Personal Protective Equipment - Footwear "
                "(Quality Control) Order, 2020"
            ),
            "notification_number": "S.O. 3857(E)",
            "issuing_ministry": (
                "Department for Promotion of Industry and Internal Trade"
            ),
            "enactment_date": "2020-10-27",
            "portal_url": (
                "https://www.bis.gov.in/product-certification/"
                "products-under-compulsory-certification/"
                "scheme-i-mark-scheme/?lang=en"
            )
        },
        "verification_status": "verified_accurate",
        "verification_note": (
            "Verified against official BIS Scheme-I listing, BIS Product "
            "Manual for IS 15298 (Part 2):2016, and BIS 2025 revision "
            "implementation circular."
        ),
        "legal_source_verified": True,
        "legal_source_verification_note": (
            "BIS lists IS 15298 (Part 2):2016 under mandatory Scheme-I "
            "certification and the Personal Protective Equipment - "
            "Footwear Quality Control Order."
        )
    },

    {
        "standard_id": "BIS-STD-102",
        "standard_number": "IS 15683",
        "part": None,
        "section": None,
        "year": "2018",
        "full_title": (
            "Portable Fire Extinguishers - Performance and Construction "
            "- Specification"
        ),
        "short_title": "Portable Fire Extinguishers",
        "product_category": "Fire Safety Equipment",
        "industry": "Fire Safety, Industrial Safety, Building Safety",
        "scheme": "Scheme-I (ISI)",
        "certification_route": "Mandatory Scheme-I Certification",
        "mandatory_qco": True,
        "status": "Active / Mandatory QCO",
        "publication_date": "2018",
        "revision_date": None,
        "supersedes": "Previous edition of IS 15683",
        "superseded_by": None,
        "amendments": [],
        "scope": (
            "Specifies performance, reliability, safety and construction "
            "requirements for portable fire extinguishers. It covers "
            "portable extinguishers intended for different classes of fire "
            "and includes requirements for construction, pressure, "
            "operation, reliability and fire-fighting performance."
        ),
        "key_testing_parameters": [
            "General operating performance",
            "Pressure requirements",
            "Resistance to temperature changes",
            "Leakage test",
            "Impact resistance",
            "Vibration resistance",
            "Resistance to corrosion",
            "Intermittent discharge test",
            "Rating suitability for different classes of fire",
            "Electrical conductivity of extinguisher discharge",
            "Construction requirements"
        ],
        "materials": [
            "Steel",
            "Aluminium",
            "Approved composite materials",
            "Fire-extinguishing media"
        ],
        "keywords": [
            "IS 15683",
            "IS 15683:2018",
            "portable fire extinguisher",
            "portable fire extinguishers",
            "fire extinguisher",
            "Class A fires",
            "Class B fires",
            "ABC extinguisher",
            "BC extinguisher",
            "CO2 extinguisher",
            "foam extinguisher",
            "water extinguisher",
            "fire safety"
        ],
        "document_url": (
            "https://www.bis.gov.in/product-certification/"
            "product-specific-information-2/product-manualsmk/"
        ),
        "source_url": (
            "https://www.bis.gov.in/product-certification/"
            "products-under-compulsory-certification/"
            "scheme-i-mark-scheme/?lang=en"
        ),
        "source_type": "Official BIS Product Manual / Scheme-I",
        "source_date": "2025-06-02",
        "retrieved_at": "2026-09-10T00:00:00Z",
        "legal_source": {
            "gazette_order": "Fire Extinguishers (Quality Control) Order, 2023",
            "notification_number": "S.O. 3585(E)",
            "issuing_ministry": (
                "Department for Promotion of Industry and Internal Trade"
            ),
            "enactment_date": "2023-08-09",
            "portal_url": (
                "https://www.bis.gov.in/wp-content/uploads/2023/08/"
                "Fire-Extinguisher-QCO-2023.pdf"
            )
        },
        "verification_status": "verified_accurate",
        "verification_note": (
            "Verified against official BIS Scheme-I listing, BIS fire "
            "extinguisher product material, BIS LIMS and Fire Extinguishers "
            "Quality Control Order, 2023."
        ),
        "legal_source_verified": True,
        "legal_source_verification_note": (
            "IS 15683:2018 is included under the Fire Extinguishers "
            "Quality Control Order, 2023 and mandatory Scheme-I certification."
        )
    }
]


with open(FILE, "r", encoding="utf-8") as f:
    data = json.load(f)


existing_numbers = {
    (
        item.get("standard_number"),
        item.get("part"),
        item.get("year")
    )
    for item in data
}


added = 0

for standard in new_standards:

    key = (
        standard["standard_number"],
        standard["part"],
        standard["year"]
    )

    if key in existing_numbers:
        print(
            f"SKIPPED: {standard['standard_number']} "
            f"{standard['part']} {standard['year']}"
        )
        continue

    data.append(standard)
    added += 1

    print(
        f"ADDED: {standard['standard_number']} "
        f"{standard['part']}:{standard['year']}"
    )


with open(FILE, "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        indent=2,
        ensure_ascii=False
    )


print()
print(f"Original records: {len(data) - added}")
print(f"Added records:    {added}")
print(f"Total records:    {len(data)}")