import json
import os
import re
import math
from collections import defaultdict


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

PROCESSED_DIR = os.path.join(
    DATA_DIR,
    "processed"
)

NORMALIZED_DIR = os.path.join(
    DATA_DIR,
    "normalized"
)

LOCAL_EMBEDDINGS_PATH = os.path.join(
    PROCESSED_DIR,
    "local_knowledge_embeddings.jsonl"
)

EMBEDDING_CHUNKS_PATH = os.path.join(
    PROCESSED_DIR,
    "embedding_chunks.json"
)

STANDARDS_PATH = os.path.join(
    NORMALIZED_DIR,
    "standards",
    "bis_standards_master.json"
)

QCO_LINKS_PATH = os.path.join(
    NORMALIZED_DIR,
    "standards",
    "standard_qco_links.json"
)

LIMS_TESTS_DIR = os.path.join(
    NORMALIZED_DIR,
    "labs"
)

MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


# ============================================================
# IS NUMBER EXTRACTION
# ============================================================

def extract_is_numbers(query):

    patterns = [
        r"\bIS\s*(?:No\.?\s*)?(\d{3,6})\b",
        r"\bI\.S\.?\s*(?:No\.?\s*)?(\d{3,6})\b",
    ]

    numbers = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            query,
            re.IGNORECASE
        )

        for match in matches:

            value = str(match).strip()

            if value and value not in numbers:
                numbers.append(value)

    return numbers


# ============================================================
# INTENT DETECTION
# ============================================================

def detect_intent(query):

    text = query.lower()

    is_numbers = extract_is_numbers(
        query
    )

    # --------------------------------------------------------
    # LABORATORY
    # --------------------------------------------------------

    lab_terms = (
        "laborator",
        "lab ",
        "testing lab",
        "test lab",
        "test laborator",
        "where can i test",
        "where to test",
        "can test",
        "testing facility",
        "testing centre",
        "testing center",
        "laboratory",
    )

    # --------------------------------------------------------
    # QCO
    # --------------------------------------------------------

    qco_terms = (
        "qco",
        "quality control order",
        "quality control orders",
        "mandatory order",
        "regulatory order",
    )

    # --------------------------------------------------------
    # TESTING
    # --------------------------------------------------------

    testing_terms = (
        "what tests",
        "which tests",
        "tests required",
        "required tests",
        "testing requirements",
        "test requirements",
        "what testing",
        "which testing",
        "tests for",
        "test for",
        "chemical requirement",
        "physical requirement",
        "testing requirement",
        "test method",
        "test methods",
        "clause requirement",
        "requirements under clause",
        "requirement under clause",
        "requirements of clause",
        "requirement of clause",
        "clause ",
        "chemical requirements",
        "physical requirements",
        "testing procedure",
        "testing procedures",
        "test procedure",
        "test procedures",
    )

    # --------------------------------------------------------
    # STANDARD
    # --------------------------------------------------------

    standard_terms = (
        "which standard",
        "what standard",
        "applicable standard",
        "applicable bis",
        "bis standard",
        "indian standard",
        "standard applies",
        "standard for",
        "which bis",
        "what bis",
    )

    # --------------------------------------------------------
    # PRIORITY
    # --------------------------------------------------------

    if any(
        term in text
        for term in lab_terms
    ):
        return "laboratory"

    if any(
        term in text
        for term in qco_terms
    ):
        return "qco"

    if is_numbers and any(
        term in text
        for term in testing_terms
    ):
        return "testing"

    if any(
        term in text
        for term in standard_terms
    ):
        return "standard"

    if is_numbers:
        return "standard"

    return "general"


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(a, b):

    if not a or not b:
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for x, y in zip(a, b):

        dot += x * y
        norm_a += x * x
        norm_b += y * y

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (
        math.sqrt(norm_a)
        * math.sqrt(norm_b)
    )


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_search_text(value):

    if value is None:
        return ""

    text = str(value).lower()

    # Replace punctuation/separators with spaces.
    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    # Collapse whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# HYBRID RETRIEVER
# ============================================================

class HybridRetriever:

    def __init__(self):

        self.semantic_embeddings = []
        self.embedding_vectors = {}

        self.standards = []
        self.standards_by_number = {}
        self.standards_by_title = []

        self.qco_links = []
        self.qco_by_number = defaultdict(list)

        self.lims_tests = []

        self._load_semantic_embeddings()
        self._load_standards()
        self._load_qco()
        self._load_lims_tests()

    # ========================================================
    # LOAD SEMANTIC EMBEDDINGS
    # ========================================================

    def _load_semantic_embeddings(self):

        print(
            "Loading semantic embeddings..."
        )

        if not os.path.exists(
            LOCAL_EMBEDDINGS_PATH
        ):

            print(
                "Local embeddings file not found"
            )

            return

        try:

            with open(
                LOCAL_EMBEDDINGS_PATH,
                "r",
                encoding="utf-8"
            ) as f:

                for line in f:

                    line = line.strip()

                    if not line:
                        continue

                    record = json.loads(
                        line
                    )

                    if not isinstance(
                        record,
                        dict
                    ):
                        continue

                    chunk_id = record.get(
                        "chunk_id"
                    )

                    vector = (
                        record.get("embedding")
                        or record.get("vector")
                    )

                    if chunk_id and vector:

                        self.embedding_vectors[
                            chunk_id
                        ] = vector

            if not os.path.exists(
                EMBEDDING_CHUNKS_PATH
            ):

                print(
                    "Embedding chunks file not found"
                )

                return

            with open(
                EMBEDDING_CHUNKS_PATH,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if isinstance(
                data,
                dict
            ):

                chunks = (
                    data.get("chunks")
                    or data.get("documents")
                    or list(data.values())
                )

            else:

                chunks = data

            chunk_by_id = {}

            for item in chunks:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                chunk_id = item.get(
                    "chunk_id"
                )

                if chunk_id:

                    chunk_by_id[
                        chunk_id
                    ] = item

            for (
                chunk_id,
                vector
            ) in self.embedding_vectors.items():

                chunk = chunk_by_id.get(
                    chunk_id
                )

                if not chunk:
                    continue

                self.semantic_embeddings.append({

                    "chunk_id": chunk_id,

                    "vector": vector,

                    "text": chunk.get(
                        "text",
                        ""
                    ),

                    "document_type": (
                        chunk.get(
                            "document_type"
                        )
                    ),

                    "standard_number": (
                        chunk.get(
                            "standard_number"
                        )
                        or chunk.get(
                            "indian_standard_no"
                        )
                    ),

                    "title": (
                        chunk.get(
                            "title"
                        )
                    ),

                    "source": (
                        chunk.get(
                            "source"
                        )
                    ),
                })

            print(
                f"Semantic chunks: "
                f"{len(self.semantic_embeddings)}"
            )

        except Exception as e:

            print(
                f"Semantic embedding load error: {e}"
            )

    # ========================================================
    # LOAD STANDARDS
    # ========================================================

    def _load_standards(self):

        print(
            "Loading standards..."
        )

        if not os.path.exists(
            STANDARDS_PATH
        ):

            print(
                "Standards file not found"
            )

            return

        try:

            with open(
                STANDARDS_PATH,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if isinstance(
                data,
                dict
            ):

                if "standards" in data:

                    data = data[
                        "standards"
                    ]

                else:

                    data = list(
                        data.values()
                    )

            if not isinstance(
                data,
                list
            ):

                data = []

            self.standards = data

            # ------------------------------------------------
            # NUMBER INDEX
            # ------------------------------------------------

            for item in self.standards:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                number = (
                    item.get(
                        "standard_number"
                    )
                    or item.get(
                        "is_number"
                    )
                    or item.get(
                        "number"
                    )
                )

                if not number:
                    continue

                normalized = (
                    self._normalize_is_number(
                        number
                    )
                )

                self.standards_by_number.setdefault(
                    normalized,
                    []
                ).append(
                    item
                )

            # ------------------------------------------------
            # TITLE INDEX
            # ------------------------------------------------

            self.standards_by_title = []

            for item in self.standards:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                title = (
                    item.get(
                        "title"
                    )
                    or ""
                )

                if not title:
                    continue

                standard_number = (
                    item.get(
                        "standard_number"
                    )
                    or item.get(
                        "is_number"
                    )
                    or item.get(
                        "number"
                    )
                )

                self.standards_by_title.append({

                    "standard_number": (
                        standard_number
                    ),

                    "title": title,

                    "department": (
                        item.get(
                            "department"
                        )
                    ),

                    "sectional_committee": (
                        item.get(
                            "sectional_committee"
                        )
                    ),

                    "type": (
                        item.get(
                            "type"
                        )
                    ),

                    "published_on": (
                        item.get(
                            "published_on"
                        )
                    ),

                    "source": (
                        "BIS Standards Catalogue"
                    ),
                })

            print(
                f"Standards: "
                f"{len(self.standards)}"
            )

            print(
                f"Standard title index: "
                f"{len(self.standards_by_title)}"
            )

        except Exception as e:

            print(
                f"Standards load error: {e}"
            )

    # ========================================================
    # LOAD QCO
    # ========================================================

    def _load_qco(self):

        print(
            "Loading QCO relationships..."
        )

        if not os.path.exists(
            QCO_LINKS_PATH
        ):

            print(
                "QCO links file not found"
            )

            return

        try:

            with open(
                QCO_LINKS_PATH,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if isinstance(
                data,
                dict
            ):

                if "links" in data:

                    data = data[
                        "links"
                    ]

                else:

                    data = list(
                        data.values()
                    )

            if not isinstance(
                data,
                list
            ):

                data = []

            self.qco_links = data

            for item in self.qco_links:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                numbers = (
                    item.get(
                        "matched_is_numbers"
                    )
                    or []
                )

                if not numbers:

                    number = item.get(
                        "standard_number"
                    )

                    if number:

                        numbers = [
                            number
                        ]

                for number in numbers:

                    normalized = (
                        self._normalize_is_number(
                            number
                        )
                    )

                    self.qco_by_number[
                        normalized
                    ].append(
                        item
                    )

            print(
                f"QCO links: "
                f"{len(self.qco_links)}"
            )

        except Exception as e:

            print(
                f"QCO load error: {e}"
            )

    # ========================================================
    # LOAD LIMS TESTS
    # ========================================================

    def _load_lims_tests(self):

        print(
            "Loading LIMS tests..."
        )

        if not os.path.exists(
            LIMS_TESTS_DIR
        ):

            print(
                "LIMS directory not found"
            )

            return

        files = []

        for root, _, filenames in os.walk(
            LIMS_TESTS_DIR
        ):

            for filename in filenames:

                if filename.lower().endswith(
                    ".json"
                ):

                    files.append(
                        os.path.join(
                            root,
                            filename
                        )
                    )

        total = 0

        for path in files:

            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    data = json.load(f)

                records = []

                if isinstance(
                    data,
                    list
                ):

                    records = data

                elif isinstance(
                    data,
                    dict
                ):

                    for key in (
                        "tests",
                        "records",
                        "capabilities",
                        "labs",
                        "data"
                    ):

                        value = data.get(
                            key
                        )

                        if isinstance(
                            value,
                            list
                        ):

                            records.extend(
                                value
                            )

                for item in records:

                    if not isinstance(
                        item,
                        dict
                    ):
                        continue

                    self.lims_tests.append(
                        item
                    )

                    total += 1

            except Exception:
                continue

        print(
            f"LIMS tests: {total}"
        )

    # ========================================================
    # NORMALIZE IS NUMBER
    # ========================================================

    @staticmethod
    def _normalize_is_number(
        value
    ):

        if not value:
            return ""

        text = str(
            value
        ).upper()

        match = re.search(
            r"IS\s*(?:NO\.?\s*)?(\d{3,6})",
            text
        )

        if match:

            return match.group(
                1
            )

        match = re.search(
            r"\b(\d{3,6})\b",
            text
        )

        if match:

            return match.group(
                1
            )

        return text.strip()

    # ========================================================
    # EXACT STANDARD SEARCH
    # ========================================================

    def exact_standards(
        self,
        is_numbers
    ):

        results = []

        for number in is_numbers:

            normalized = (
                self._normalize_is_number(
                    number
                )
            )

            matches = (
                self.standards_by_number.get(
                    normalized,
                    []
                )
            )

            for item in matches:

                result = dict(
                    item
                )

                result[
                    "match_type"
                ] = "exact"

                results.append(
                    result
                )

        return self._deduplicate_results(
            results
        )

    # ========================================================
    # STANDARD KEYWORD SEARCH
    # ========================================================

    def standard_keyword_search(
        self,
        query,
        limit=8
    ):
        """
        Deterministic product/title search against
        the BIS Standards Catalogue.

        Example:
            Which BIS standard applies to composite cement?

        Expected:
            IS 16415:2015
            Composite Cement - Specification
        """

        if not self.standards_by_title:
            return []

        query_text = normalize_search_text(
            query
        )

        # ----------------------------------------------------
        # Remove question words / generic BIS words
        # ----------------------------------------------------

        stop_words = {
            "which",
            "what",
            "where",
            "when",
            "how",
            "does",
            "do",
            "is",
            "are",
            "the",
            "a",
            "an",
            "bis",
            "standard",
            "standards",
            "indian",
            "applies",
            "apply",
            "applicable",
            "application",
            "used",
            "use",
            "required",
            "requirements",
            "for",
            "to",
            "my",
            "product",
            "under",
            "with",
            "of",
        }

        query_terms = [
            term
            for term in query_text.split()
            if (
                len(term) > 2
                and term not in stop_words
            )
        ]

        query_term_set = set(
            query_terms
        )

        if not query_term_set:
            return []

        # ----------------------------------------------------
        # Extract product phrase
        # ----------------------------------------------------

        product_phrase = query_text

        prefixes = (
            "which bis standard applies to ",
            "what bis standard applies to ",
            "which standard applies to ",
            "what standard applies to ",
            "which bis standard is applicable to ",
            "what bis standard is applicable to ",
            "which bis standard is used for ",
            "what bis standard is used for ",
            "bis standard for ",
            "standard for ",
            "which bis standard for ",
            "what bis standard for ",
        )

        for prefix in prefixes:

            if product_phrase.startswith(
                prefix
            ):

                product_phrase = (
                    product_phrase[
                        len(prefix):
                    ]
                )

                break

        product_phrase = normalize_search_text(
            product_phrase
        )

        # ----------------------------------------------------
        # If phrase still contains generic terms,
        # clean it again.
        # ----------------------------------------------------

        product_terms = [
            term
            for term in product_phrase.split()
            if (
                len(term) > 2
                and term not in stop_words
            )
        ]

        product_phrase_clean = " ".join(
            product_terms
        )

        scored = []

        # ----------------------------------------------------
        # Compare against every BIS standard title
        # ----------------------------------------------------

        for standard in self.standards_by_title:

            title = (
                standard.get(
                    "title"
                )
                or ""
            )

            title_normalized = normalize_search_text(
                title
            )

            if not title_normalized:
                continue

            title_terms = set(
                title_normalized.split()
            )

            matched_terms = (
                query_term_set
                & title_terms
            )

            # ------------------------------------------------
            # Partial token matching
            # ------------------------------------------------

            partial_matches = set()

            for query_term in query_term_set:

                for title_term in title_terms:

                    if (
                        query_term == title_term
                    ):
                        continue

                    if (
                        query_term in title_term
                        or title_term in query_term
                    ):

                        if (
                            len(query_term) >= 4
                            and len(title_term) >= 4
                        ):

                            partial_matches.add(
                                query_term
                            )

            all_matches = (
                matched_terms
                | partial_matches
            )

            if not all_matches:
                continue

            # ------------------------------------------------
            # Score
            # ------------------------------------------------

            score = 0

            # Exact token matches.
            score += (
                len(matched_terms)
                * 5
            )

            # Partial token matches.
            score += (
                len(partial_matches)
                * 2
            )

            # Complete product phrase in title.
            if (
                product_phrase_clean
                and product_phrase_clean
                in title_normalized
            ):

                score += 30

            # Exact title match.
            if (
                product_phrase_clean
                == title_normalized
            ):

                score += 50

            # More matching coverage gets a bonus.
            if query_term_set:

                coverage = (
                    len(all_matches)
                    / len(query_term_set)
                )

                score += coverage * 10

            scored.append(
                (
                    score,
                    standard
                )
            )

        # ----------------------------------------------------
        # Sort
        # ----------------------------------------------------

        scored.sort(
            key=lambda item: (
                item[0],
                item[1].get(
                    "standard_number"
                ) or "",
            ),
            reverse=True
        )

        # ----------------------------------------------------
        # Build results
        # ----------------------------------------------------

        results = []

        for score, standard in scored[:limit]:

            result = dict(
                standard
            )

            result[
                "match_type"
            ] = "keyword"

            result[
                "keyword_score"
            ] = round(
                score,
                3
            )

            results.append(
                result
            )

        return results

    # ========================================================
    # SEMANTIC SEARCH
    # ========================================================

    def semantic_search(
        self,
        query,
        limit=8
    ):

        if not self.semantic_embeddings:
            return []

        try:

            from sentence_transformers import (
                SentenceTransformer
            )

            model = SentenceTransformer(
                MODEL_NAME
            )

            query_vector = model.encode(
                query,
                normalize_embeddings=True
            )

            scored = []

            for item in self.semantic_embeddings:

                score = cosine_similarity(
                    query_vector,
                    item["vector"]
                )

                scored.append(
                    (
                        score,
                        item
                    )
                )

            scored.sort(
                key=lambda x: x[0],
                reverse=True
            )

            results = []

            for score, item in scored[:limit]:

                result = dict(
                    item
                )

                result[
                    "distance"
                ] = 1 - score

                result[
                    "similarity"
                ] = score

                results.append(
                    result
                )

            return results

        except Exception as e:

            print(
                f"Semantic search error: {e}"
            )

            return []

    # ========================================================
    # QCO SEARCH
    # ========================================================

    def qco_search(
        self,
        is_numbers
    ):

        results = []

        for number in is_numbers:

            normalized = (
                self._normalize_is_number(
                    number
                )
            )

            matches = (
                self.qco_by_number.get(
                    normalized,
                    []
                )
            )

            for item in matches:

                result = dict(
                    item
                )

                result[
                    "match_type"
                ] = "qco_relationship"

                results.append(
                    result
                )

        return self._deduplicate_results(
            results
        )

    # ========================================================
    # LAB SEARCH
    # ========================================================

    def lab_search(
        self,
        is_numbers,
        limit=20
    ):

        if not is_numbers:
            return []

        wanted = {
            self._normalize_is_number(
                number
            )
            for number in is_numbers
        }

        results = []

        for item in self.lims_tests:

            number = (
                item.get(
                    "standard_number"
                )
                or item.get(
                    "is_number"
                )
                or item.get(
                    "standard"
                )
                or item.get(
                    "indian_standard_no"
                )
            )

            if not number:
                continue

            normalized = (
                self._normalize_is_number(
                    number
                )
            )

            if normalized not in wanted:
                continue

            lab_name = (
                item.get(
                    "lab_name"
                )
                or item.get(
                    "laboratory"
                )
                or item.get(
                    "lab"
                )
            )

            if not lab_name:
                continue

            result = dict(
                item
            )

            result[
                "standard_number"
            ] = number

            result[
                "match_type"
            ] = "lims_lab"

            results.append(
                result
            )

            if len(results) >= limit:
                break

        return self._deduplicate_results(
            results
        )

    # ========================================================
    # TEST SEARCH
    # ========================================================

    def test_search(
        self,
        is_numbers,
        limit=50
    ):

        if not is_numbers:
            return []

        wanted = {
            self._normalize_is_number(
                number
            )
            for number in is_numbers
        }

        results = []
        seen = set()

        for item in self.lims_tests:

            number = (
                item.get(
                    "standard_number"
                )
                or item.get(
                    "is_number"
                )
                or item.get(
                    "standard"
                )
                or item.get(
                    "indian_standard_no"
                )
            )

            if not number:
                continue

            normalized = (
                self._normalize_is_number(
                    number
                )
            )

            if normalized not in wanted:
                continue

            key = (
                normalized,
                item.get(
                    "lab_code"
                ),
                item.get(
                    "lab_name"
                ),
                item.get(
                    "product"
                ),
                item.get(
                    "designation"
                ),
                item.get(
                    "testing_charge_raw"
                ),
                item.get(
                    "test_name"
                ),
                item.get(
                    "clause"
                ),
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            result = dict(
                item
            )

            result[
                "standard_number"
            ] = number

            result[
                "match_type"
            ] = "lims_test"

            results.append(
                result
            )

            if len(results) >= limit:
                break

        return results

    # ========================================================
    # DEDUPLICATION
    # ========================================================

    @staticmethod
    def _deduplicate_results(
        results
    ):

        seen = set()
        output = []

        for item in results:

            try:

                key = json.dumps(
                    item,
                    sort_keys=True,
                    ensure_ascii=False,
                    default=str
                )

            except Exception:

                key = str(
                    item
                )

            if key in seen:
                continue

            seen.add(
                key
            )

            output.append(
                item
            )

        return output

    # ========================================================
    # MAIN SEARCH
    # ========================================================

    def search(
        self,
        query,
        semantic_limit=8,
        lab_limit=20
    ):

        is_numbers = extract_is_numbers(
            query
        )

        intent = detect_intent(
            query
        )

        semantic = []
        exact = []
        qco = []
        labs = []
        tests = []

        # ----------------------------------------------------
        # LABORATORY
        # ----------------------------------------------------

        if intent == "laboratory":

            exact = self.exact_standards(
                is_numbers
            )

            labs = self.lab_search(
                is_numbers,
                lab_limit
            )

        # ----------------------------------------------------
        # QCO
        # ----------------------------------------------------

        elif intent == "qco":

            exact = self.exact_standards(
                is_numbers
            )

            qco = self.qco_search(
                is_numbers
            )

        # ----------------------------------------------------
        # TESTING
        # ----------------------------------------------------

        elif intent == "testing":

            exact = self.exact_standards(
                is_numbers
            )

            tests = self.test_search(
                is_numbers,
                50
            )

        # ----------------------------------------------------
        # STANDARD
        # ----------------------------------------------------

        elif intent == "standard":

            # -----------------------------------------------
            # Semantic retrieval
            # -----------------------------------------------

            semantic = self.semantic_search(
                query,
                semantic_limit
            )

            # -----------------------------------------------
            # Exact IS-number retrieval
            # -----------------------------------------------

            exact = self.exact_standards(
                is_numbers
            )

            # -----------------------------------------------
            # Deterministic title/product retrieval
            # -----------------------------------------------

            keyword_results = (
                self.standard_keyword_search(
                    query,
                    semantic_limit
                )
            )

            exact.extend(
                keyword_results
            )

            exact = (
                self._deduplicate_results(
                    exact
                )
            )

        # ----------------------------------------------------
        # GENERAL
        # ----------------------------------------------------

        else:

            semantic = self.semantic_search(
                query,
                semantic_limit
            )

            exact = self.exact_standards(
                is_numbers
            )

            if is_numbers:

                qco = self.qco_search(
                    is_numbers
                )

        return {
            "query": query,
            "intent": intent,
            "is_numbers": is_numbers,
            "semantic": semantic,
            "exact_standards": exact,
            "qco": qco,
            "labs": labs,
            "tests": tests,
        }


# ============================================================
# GLOBAL RETRIEVER
# ============================================================

try:

    hybrid_retriever = HybridRetriever()

except Exception as e:

    print(
        f"Hybrid retriever initialization failed: {e}"
    )

    hybrid_retriever = None


# ============================================================
# PUBLIC SEARCH FUNCTION
# ============================================================

def search(
    query,
    semantic_limit=8,
    lab_limit=20
):

    if hybrid_retriever is None:

        return {
            "query": query,
            "intent": detect_intent(
                query
            ),
            "is_numbers": extract_is_numbers(
                query
            ),
            "semantic": [],
            "exact_standards": [],
            "qco": [],
            "labs": [],
            "tests": [],
        }

    return hybrid_retriever.search(
        query,
        semantic_limit,
        lab_limit
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    retriever = HybridRetriever()

    print()
    print("=" * 70)
    print("StandIQ Hybrid Retriever")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # Automatic sanity test
    # --------------------------------------------------------

    test_query = (
        "Which BIS standard applies to composite cement?"
    )

    print(
        "AUTOMATIC TEST:"
    )

    print(
        test_query
    )

    print()

    print(
        "Intent:",
        detect_intent(
            test_query
        )
    )

    print()

    keyword_results = (
        retriever.standard_keyword_search(
            test_query,
            10
        )
    )

    print(
        "Keyword standard results:"
    )

    if not keyword_results:

        print(
            "NO RESULTS"
        )

    else:

        for index, item in enumerate(
            keyword_results,
            1
        ):

            print(
                f"{index}. "
                f"{item.get('standard_number')} "
                f"| "
                f"{item.get('title')} "
                f"| "
                f"score={item.get('keyword_score')} "
                f"| "
                f"{item.get('match_type')}"
            )

    print()
    print("=" * 70)
    print(
        "Interactive mode"
    )
    print(
        "Type 'exit' to quit."
    )
    print("=" * 70)

    while True:

        try:

            query = input(
                "\nEnter query: "
            ).strip()

        except (
            EOFError,
            KeyboardInterrupt
        ):

            print()
            break

        if query.lower() == "exit":
            break

        if not query:
            continue

        result = retriever.search(
            query
        )

        print()
        print(
            "=== INTENT ==="
        )

        print(
            result["intent"]
        )

        print()
        print(
            "=== IS NUMBERS ==="
        )

        print(
            result["is_numbers"]
        )

        print()
        print(
            "=== STANDARDS ==="
        )

        standards = result[
            "exact_standards"
        ]

        if not standards:

            print(
                "No standards found."
            )

        else:

            for item in standards[:10]:

                print(
                    item.get(
                        "standard_number"
                    ),
                    "|",
                    item.get(
                        "title"
                    ),
                    "|",
                    item.get(
                        "match_type"
                    ),
                    "|",
                    item.get(
                        "keyword_score",
                        ""
                    )
                )

        print()
        print(
            "=== SEMANTIC RESULTS ==="
        )

        if not result["semantic"]:

            print(
                "No semantic results."
            )

        else:

            for i, item in enumerate(
                result["semantic"],
                1
            ):

                print(
                    f"{i}. "
                    f"{item.get('similarity', 0):.4f} | "
                    f"{item.get('document_type')} | "
                    f"{item.get('standard_number')} | "
                    f"{item.get('title')}"
                )

        print()
        print(
            "=== QCO ==="
        )

        if not result["qco"]:

            print(
                "No QCO results."
            )

        else:

            for item in result["qco"]:

                print(
                    item.get(
                        "standard_number"
                    ),
                    "|",
                    item.get(
                        "relationship"
                    ),
                    "|",
                    item.get(
                        "qco_document_id"
                    )
                )

        print()
        print(
            "=== LABS ==="
        )

        if not result["labs"]:

            print(
                "No laboratory results."
            )

        else:

            for item in result["labs"]:

                print(
                    item.get(
                        "lab_name"
                    ),
                    "|",
                    item.get(
                        "lab_code"
                    ),
                    "|",
                    item.get(
                        "standard_number"
                    ),
                    "|",
                    item.get(
                        "product"
                    )
                )

        print()
        print(
            "=== TESTS ==="
        )

        if not result["tests"]:

            print(
                "No testing results."
            )

        else:

            for item in result["tests"][:10]:

                print(
                    item.get(
                        "standard_number"
                    ),
                    "|",
                    item.get(
                        "product"
                    ),
                    "|",
                    item.get(
                        "clause"
                    )
                )