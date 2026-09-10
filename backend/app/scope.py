import re


BIS_KEYWORDS = [
    "bis",
    "bureau of indian standards",
    "indian standard",
    "indian standards",
    "is ",
    "scheme-i",
    "scheme-ii",
    "isi",
    "crs",
    "qco",
    "quality control order",
    "hallmark",
    "huid",
    "certification",
    "standard",
    "standards",
]


def is_bis_related(query: str) -> bool:
    """
    Lightweight first-pass scope checker.

    Returns True when the query contains terminology
    strongly associated with BIS / Indian Standards.
    """

    if not query:
        return False

    query_lower = query.lower().strip()

    for keyword in BIS_KEYWORDS:

        if keyword == "is ":
            # Match "IS 1786", "IS 456", etc.
            if re.search(r"\bis\s+\d", query_lower):
                return True

        elif keyword in query_lower:
            return True

    # Product/domain terms that commonly map to BIS standards.
    product_terms = [
        "pressure cooker",
        "power bank",
        "gold jewellery",
        "gold jewelry",
        "helmet",
        "packaged drinking water",
        "tmt",
        "steel bar",
        "steel bars",
        "toy",
        "toys",
        "led",
        "cable",
        "plug",
        "socket",
        "smart meter",
        "tyre",
        "tires",
        "safety glass",
        "hdpe pipe",
        "plywood",
        "geyser",
        "water heater",
        "safety shoes",
        "fire extinguisher",
        "solar pv",
        "solar panel",
        "pos machine",
        "cookware",
        "electric motor",
        "ceiling fan",
        "kitchen chimney",
        "range hood",
        "ev charging",
        "evse",
        "biometric",
        "aadhaar",
        "roofing sheet",
        "structural steel",
        "cement",
        "concrete",
        "steel tube",
        "transformer",
    ]

    for term in product_terms:

        if term in query_lower:
            return True

    return False


def get_scope_response():
    return {
        "answer": (
            "I'm StandIQ, an assistant focused on BIS standards, "
            "Indian Standards, BIS certification, and related "
            "Quality Control Orders. I can only answer questions "
            "within that scope."
        ),
        "sources": []
    }