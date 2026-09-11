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
    "ప్రమాణం",
    "ప్రమాణాలు",
    "ధృవీకరణ",
    "హాల్‌మార్కింగ్",
    "హాల్మార్కింగ్",
    "मानक",
    "मानकों",
    "प्रमाणन",
    "हॉलमार्किंग",
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
        "ప్రెజర్ కుక్కర్",
        "స్టీల్",
        "బంగారం",
        "హెల్మెట్",
        "నీరు",
        "బొమ్మలు",
        "प्रेशर कुकर",
        "स्टील",
        "सोना",
        "हेलमेट",
        "पानी",
        "खिलौने",
    ]

    for term in product_terms:

        if term in query_lower:
            return True

    return False


def get_scope_response(language="en"):
    responses = {
        "te": (
            "నేను BIS ప్రమాణాలు, భారతీయ ప్రమాణాలు, BIS ధృవీకరణ మరియు "
            "సంబంధిత Quality Control Orders గురించి మాత్రమే సహాయం చేయగలను. "
            "ఈ పరిధిలోని ప్రశ్నలను అడగండి."
        ),
        "hi": (
            "मैं BIS मानकों, भारतीय मानकों, BIS प्रमाणन और संबंधित Quality "
            "Control Orders के बारे में ही सहायता कर सकता हूँ। कृपया इसी "
            "दायरे में प्रश्न पूछें।"
        ),
    }

    return {
        "answer": responses.get(language, (
            "I'm StandIQ, an assistant focused on BIS standards, "
            "Indian Standards, BIS certification, and related "
            "Quality Control Orders. I can only answer questions "
            "within that scope."
        )),
        "sources": []
    }