import re


LANGUAGE_NAMES = {
    "en": "English",
    "te": "Telugu",
    "hi": "Hindi",
}

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in natural English.",
    "te": (
        "Answer entirely in Telugu (తెలుగు). Translate every explanatory "
        "sentence, heading, bullet, standard title, and description. Do not "
        "copy English BIS titles or descriptions. Preserve only official "
        "identifiers such as IS numbers, BIS, ISI, QCO, Scheme-I, Scheme-II, "
        "URLs, and official codes."
    ),
    "hi": (
        "Answer entirely in Hindi (हिन्दी). Translate every explanatory "
        "sentence, heading, bullet, standard title, and description. Do not "
        "copy English BIS titles or descriptions. Preserve only official "
        "identifiers such as IS numbers, BIS, ISI, QCO, Scheme-I, Scheme-II, "
        "URLs, and official codes."
    ),
}

SEMANTIC_TRANSLATION_GUIDANCE = {
    "en": "Use natural English.",
    "te": (
        "Translate meaning, not pronunciation. Never transliterate an English "
        "title or sentence into Telugu script. For example, translate "
        "'High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - "
        "Specification' as 'కాంక్రీట్‌లో ఉపబలానికి ఉపయోగించే అధిక బలం కలిగిన "
        "డీఫార్మ్డ్ స్టీల్ బార్లు మరియు వైర్లకు సంబంధించిన ప్రమాణం'. Prefer "
        "'ప్రమాణం' for Specification, 'ధృవీకరణ' for Certification, "
        "'పరీక్షా అవసరాలు' for Testing requirements, and 'తన్యతా బలం' for "
        "Tensile strength. Technical concepts must be expressed by meaning; "
        "use transliterated terms only when no natural equivalent exists. "
        "Never write phrases such as 'హై స్ట్రెంగ్త్ ... ఫర్ కాంక్రీట్ "
        "రీఇన్ఫోర్స్‌మెంట్' or 'టెన్సైల్ స్ట్రెంగ్త్ రేషియో'."
    ),
    "hi": (
        "Translate meaning, not pronunciation. Never transliterate an English "
        "title or sentence into Devanagari. For example, translate "
        "'High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - "
        "Specification' as 'कंक्रीट में सुदृढ़ीकरण के लिए उच्च शक्ति वाले "
        "विकृत स्टील बार और वायर से संबंधित मानक'. Prefer 'मानक' or "
        "'विनिर्देश' for Specification, 'प्रमाणन' for Certification, "
        "'परीक्षण आवश्यकताएँ' for Testing requirements, and 'तन्यता शक्ति' for "
        "Tensile strength. Technical concepts must be expressed by meaning; "
        "use transliterated terms only when no natural equivalent exists. "
        "Never write phrases such as 'हाई स्ट्रेंथ ... फॉर कंक्रीट "
        "रीइन्फोर्समेंट' or 'टेनसाइल स्ट्रेंथ रेशियो'."
    ),
}

TELUGU_RE = re.compile(r"[\u0c00-\u0c7f]")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")
LATIN_RE = re.compile(r"[a-zA-Z]")

# These terms provide an English retrieval signal without changing the user's question.
RETRIEVAL_HINTS = {
    "te": {
        "బిస్": "BIS",
        "ప్రమాణం": "standard",
        "ప్రమాణాలు": "standards",
        "ధృవీకరణ": "certification",
        "హాల్‌మార్కింగ్": "hallmarking",
        "హాల్మార్కింగ్": "hallmarking",
        "నాణ్యత నియంత్రణ ఆర్డర్": "quality control order",
        "ప్రెజర్ కుక్కర్": "pressure cooker",
        "కుక్కర్": "cooker",
        "స్టీల్": "steel",
        "బంగారం": "gold",
        "హెల్మెట్": "helmet",
        "నీరు": "water",
        "బొమ్మలు": "toys",
        "కేబుల్": "cable",
    },
    "hi": {
        "बीआईएस": "BIS",
        "मानक": "standard",
        "मानकों": "standards",
        "प्रमाणन": "certification",
        "हॉलमार्किंग": "hallmarking",
        "गुणवत्ता नियंत्रण आदेश": "quality control order",
        "प्रेशर कुकर": "pressure cooker",
        "कुकर": "cooker",
        "स्टील": "steel",
        "सोना": "gold",
        "हेलमेट": "helmet",
        "पानी": "water",
        "खिलौने": "toys",
        "केबल": "cable",
    },
}

TRANSLITERATED_HINTS = {
    "te": {
        "pramaanam": "standard",
        "pramanam": "standard",
        "dhruvikarana": "certification",
        "pressure cooker": "pressure cooker",
        "steel": "steel",
        "bangaram": "gold",
    },
    "hi": {
        "maanak": "standard",
        "pramaanan": "certification",
        "praman": "certification",
        "pressure cooker": "pressure cooker",
        "steel": "steel",
        "sona": "gold",
    },
}


def detect_language(query: str) -> dict[str, str]:
    """Detect English, Telugu, or Hindi from script and common transliteration."""

    text = query or ""
    telugu_count = len(TELUGU_RE.findall(text))
    hindi_count = len(DEVANAGARI_RE.findall(text))

    if telugu_count > hindi_count and telugu_count > 0:
        language = "te"
    elif hindi_count > telugu_count and hindi_count > 0:
        language = "hi"
    else:
        lower_text = text.lower()
        transliterated_scores = {
            code: sum(term in lower_text for term in hints)
            for code, hints in TRANSLITERATED_HINTS.items()
        }
        language = max(transliterated_scores, key=transliterated_scores.get)
        if transliterated_scores[language] == 0:
            language = "en"

    return {
        "language": language,
        "language_name": LANGUAGE_NAMES[language],
    }


def prepare_retrieval_query(query: str, language: str) -> str:
    """Add small English retrieval hints while preserving the original query."""

    if language not in RETRIEVAL_HINTS and language not in TRANSLITERATED_HINTS:
        return query

    lower_query = (query or "").lower()
    hints = []

    for term, english_term in RETRIEVAL_HINTS.get(language, {}).items():
        if term in lower_query:
            hints.append(english_term)

    for term, english_term in TRANSLITERATED_HINTS.get(language, {}).items():
        if term in lower_query:
            hints.append(english_term)

    if not hints:
        return query

    return f"{query} {' '.join(dict.fromkeys(hints))}"


def get_language_instruction(language: str) -> str:
    return LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])


def get_semantic_translation_guidance(language: str) -> str:
    return SEMANTIC_TRANSLATION_GUIDANCE.get(
        language,
        SEMANTIC_TRANSLATION_GUIDANCE["en"],
    )


def get_speech_language(language: str) -> str:
    return {
        "en": "en-IN",
        "te": "te-IN",
        "hi": "hi-IN",
    }.get(language, "en-IN")
