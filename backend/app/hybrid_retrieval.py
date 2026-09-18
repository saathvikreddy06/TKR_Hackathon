import json
import importlib
import os
import re
import math
import threading
import traceback
from collections import defaultdict

from app.firebase import db
from app.embedding_runtime import load_embedding_model


ijson = importlib.import_module("ijson")


os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")

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

LIMS_TESTS_PATH = os.path.join(
    LIMS_TESTS_DIR,
    "bis_lims_tests.json"
)

MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

MODEL_LOCAL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "paraphrase-multilingual-MiniLM-L12-v2"
)

FIRESTORE_COLLECTION = "standard_chunks_local"
FIRESTORE_VECTOR_FIELD = "embedding"
FIRESTORE_VECTOR_DIMENSIONS = 384


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

        for match in re.findall(
            pattern,
            query,
            re.IGNORECASE
        ):

            value = str(match).strip()

            if value and value not in numbers:
                numbers.append(value)

    return numbers


# ============================================================
# INTENT DETECTION
# ============================================================

def detect_intent(query):

    text = query.lower()
    is_numbers = extract_is_numbers(query)

    lab_terms = (
        "laborator",
        "laboratory",
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
    )

    qco_terms = (
        "qco",
        "quality control order",
        "quality control orders",
        "mandatory order",
        "regulatory order",
    )

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
# SEARCH TEXT NORMALIZATION
# ============================================================

def normalize_search_text(value):

    if value is None:
        return ""

    text = str(value).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

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
        self.firebase_vector_enabled = db is not None

        self.standards = []
        self.standards_by_number = {}
        self.standards_by_title = []

        self.qco_links = []
        self.qco_by_number = defaultdict(list)

        self.lims_tests_path = LIMS_TESTS_PATH

        self._load_semantic_embeddings()
        self._load_standards()
        self._load_qco()
        self._load_lims_tests()

    # ========================================================
    # LOAD SEMANTIC EMBEDDINGS
    # ========================================================

    def _load_semantic_embeddings(self):

        print("Configuring Firebase semantic retrieval...")

        if db is None:

            print(
                "Firebase is not connected. "
                "Semantic retrieval is disabled."
            )

            self.firebase_vector_enabled = False

            return

        self.firebase_vector_enabled = True

        print(
            "Firebase semantic collection: "
            f"{FIRESTORE_COLLECTION}"
        )

        print(
            "Firebase vector field: "
            f"{FIRESTORE_VECTOR_FIELD} "
            f"({FIRESTORE_VECTOR_DIMENSIONS} dimensions)"
        )

    # ========================================================
    # EMBEDDING MODEL
    # ========================================================

    @classmethod
    def _get_embedding_model(cls):
        return load_embedding_model()

    @classmethod
    def load_embedding_model(cls):
        """Load the build-time model before the first semantic request."""

        return cls._get_embedding_model()

    # ========================================================
    # LOAD STANDARDS
    # ========================================================

    def _load_standards(self):

        print("Loading standards...")

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

                self.standards_by_title.append({

                    "standard_number": number,

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

                    "document_id": (
                        item.get(
                            "document_id"
                        )
                    ),

                    "source": (
                        item.get(
                            "source"
                        )
                        or "BIS Standards Catalogue"
                    ),

                    "match_type": (
                        "standard_catalogue"
                    ),
                })

        except Exception as e:

            print(
                "Standards loading error:",
                repr(e)
            )

            traceback.print_exc()

            self.standards = []

    # ========================================================
    # LOAD QCO
    # ========================================================

    def _load_qco(self):

        print("Loading QCO relationships...")

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

            for item in data:

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
                        "standard_id"
                    )
                )

                if not number:
                    continue

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

        except Exception as e:

            print(
                "QCO loading error:",
                repr(e)
            )

            traceback.print_exc()

            self.qco_links = []

    # ========================================================
    # LOAD LIMS TESTS
    # ========================================================

    def _load_lims_tests(self):
        if os.path.isfile(self.lims_tests_path):
            print("LIMS tests: lazy streaming enabled")
        else:
            print("LIMS tests file not found:", self.lims_tests_path)

    def _iter_lims_tests(self):
        if not os.path.isfile(self.lims_tests_path):
            return

        try:
            with open(self.lims_tests_path, "rb") as file:
                yield from ijson.items(file, "item")
        except Exception as exc:
            print(
                "LIMS streaming error:",
                repr(exc)
            )
            traceback.print_exc()

    # ========================================================
    # IS NUMBER NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_is_number(
        value
    ):

        if value is None:
            return ""

        text = str(
            value
        ).upper().strip()

        text = re.sub(
            r"[^A-Z0-9]+",
            "",
            text
        )

        if text.startswith(
            "IS"
        ):

            text = text[2:]

        return text

    # ========================================================
    # FIREBASE SEMANTIC SEARCH
    # ========================================================

    def semantic_search(
        self,
        query,
        limit=8
    ):

        if not self.firebase_vector_enabled:

            print(
                "Semantic search skipped: "
                "Firebase vector retrieval disabled."
            )

            return []

        if db is None:

            print(
                "Semantic search skipped: "
                "Firestore database is None."
            )

            return []

        print()
        print(
            "========== FIREBASE SEMANTIC SEARCH =========="
        )
        print(
            "Query:",
            repr(query)
        )
        print(
            "Collection:",
            FIRESTORE_COLLECTION
        )
        print(
            "Vector field:",
            FIRESTORE_VECTOR_FIELD
        )
        print(
            "Vector dimensions:",
            FIRESTORE_VECTOR_DIMENSIONS
        )
        print(
            "Requested limit:",
            limit
        )

        try:

            # ------------------------------------------------
            # STEP 1: LOAD MODEL
            # ------------------------------------------------

            print(
                "Step 1: Loading embedding model..."
            )

            model = self._get_embedding_model()

            print(
                "Step 1 complete."
            )

            # ------------------------------------------------
            # STEP 2: CREATE QUERY EMBEDDING
            # ------------------------------------------------

            print(
                "Step 2: Creating query embedding..."
            )

            query_vector = model.encode(query)

            print(
                "Raw embedding type:",
                type(query_vector)
            )

            print(
                "Raw embedding shape:",
                getattr(
                    query_vector,
                    "shape",
                    None
                )
            )

            print(
                "Embedding length:",
                len(query_vector)
            )

            if len(query_vector) != FIRESTORE_VECTOR_DIMENSIONS:

                raise ValueError(
                    "Embedding dimension mismatch. "
                    f"Expected {FIRESTORE_VECTOR_DIMENSIONS}, "
                    f"got {len(query_vector)}."
                )

            print(
                "Step 2 complete."
            )

            # ------------------------------------------------
            # STEP 3: IMPORT FIRESTORE VECTOR TYPES
            # ------------------------------------------------

            print(
                "Step 3: Loading Firestore vector classes..."
            )

            from google.cloud.firestore_v1.base_vector_query import (
                DistanceMeasure
            )

            from google.cloud.firestore_v1.vector import (
                Vector
            )

            print(
                "Step 3 complete."
            )

            # ------------------------------------------------
            # STEP 4: CREATE VECTOR QUERY
            # ------------------------------------------------

            print(
                "Step 4: Creating Firestore vector query..."
            )

            vector_query = db.collection(
                FIRESTORE_COLLECTION
            ).find_nearest(
                vector_field=FIRESTORE_VECTOR_FIELD,
                query_vector=Vector(
                    query_vector
                ),
                distance_measure=DistanceMeasure.COSINE,
                limit=min(
                    max(
                        int(limit),
                        1
                    ),
                    1000
                ),
                distance_result_field="vector_distance"
            )

            print(
                "Step 4 complete."
            )

            # ------------------------------------------------
            # STEP 5: EXECUTE QUERY
            # ------------------------------------------------

            print(
                "Step 5: Executing Firestore vector query..."
            )

            documents = vector_query.stream()

            results = []

            for document in documents:

                data = document.to_dict() or {}

                metadata = (
                    data.get(
                        "metadata"
                    )
                    or {}
                )

                if not isinstance(
                    metadata,
                    dict
                ):

                    metadata = {}

                distance = data.get(
                    "vector_distance"
                )

                if distance is None:

                    distance = 1.0

                try:

                    distance = float(
                        distance
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    distance = 1.0

                result = {

                    "chunk_id": (
                        data.get(
                            "chunk_id"
                        )
                        or document.id
                    ),

                    "document_id": (
                        data.get(
                            "document_id"
                        )
                    ),

                    "document_type": (
                        data.get(
                            "document_type"
                        )
                    ),

                    "text": (
                        data.get(
                            "text"
                        )
                        or ""
                    ),

                    "standard_number": (
                        data.get(
                            "standard_number"
                        )
                        or metadata.get(
                            "standard_number"
                        )
                        or metadata.get(
                            "is_number"
                        )
                        or metadata.get(
                            "indian_standard_no"
                        )
                    ),

                    "title": (
                        data.get(
                            "title"
                        )
                        or metadata.get(
                            "title"
                        )
                        or metadata.get(
                            "standard_name"
                        )
                    ),

                    "source": (
                        data.get(
                            "source"
                        )
                        or metadata.get(
                            "source"
                        )
                        or "BIS Firestore Knowledge Base"
                    ),

                    "metadata": metadata,

                    "distance": distance,

                    "similarity": max(
                        0.0,
                        1.0 - distance
                    ),

                    "match_type": (
                        "firebase_semantic"
                    ),
                }

                results.append(
                    result
                )

            print(
                "Step 5 complete."
            )

            print(
                "Firebase semantic results:",
                len(results)
            )

            print(
                "========== FIREBASE SEARCH COMPLETE =========="
            )
            print()

            return results

        except Exception as e:

            print()
            print(
                "!!!!!!!!!! FIREBASE SEMANTIC SEARCH FAILED !!!!!!!!!!"
            )

            print(
                "Exception type:",
                type(e).__name__
            )

            print(
                "Exception:",
                repr(e)
            )

            print(
                "Query:",
                repr(query)
            )

            print(
                "Collection:",
                FIRESTORE_COLLECTION
            )

            print(
                "Vector field:",
                FIRESTORE_VECTOR_FIELD
            )

            print(
                "Expected dimensions:",
                FIRESTORE_VECTOR_DIMENSIONS
            )

            traceback.print_exc()

            print(
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            )
            print()

            # IMPORTANT:
            # Do not silently hide this failure.
            raise RuntimeError(
                "Firebase semantic retrieval failed: "
                f"{type(e).__name__}: {e}"
            ) from e

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

            for item in self.standards_by_number.get(
                normalized,
                []
            ):

                result = dict(
                    item
                )

                result[
                    "match_type"
                ] = "exact_standard"

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

        normalized_query = (
            normalize_search_text(
                query
            )
        )

        if not normalized_query:
            return []

        query_tokens = set(
            normalized_query.split()
        )

        scored = []

        for item in self.standards_by_title:

            title = (
                item.get(
                    "title"
                )
                or ""
            )

            normalized_title = (
                normalize_search_text(
                    title
                )
            )

            title_tokens = set(
                normalized_title.split()
            )

            overlap = len(
                query_tokens
                & title_tokens
            )

            if overlap == 0:
                continue

            score = overlap / max(
                len(query_tokens),
                1
            )

            result = dict(
                item
            )

            result[
                "keyword_score"
            ] = score

            result[
                "match_type"
            ] = "keyword_standard"

            scored.append(
                result
            )

        scored.sort(
            key=lambda x: x.get(
                "keyword_score",
                0
            ),
            reverse=True
        )

        return scored[:limit]

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

            for item in self.qco_by_number.get(
                normalized,
                []
            ):

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

        for item in self._iter_lims_tests():

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

            if len(
                results
            ) >= limit:

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

        for item in self._iter_lims_tests():

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

            if len(
                results
            ) >= limit:

                break

        return self._deduplicate_results(
            results
        )

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

        print()
        print(
            "========== HYBRID SEARCH =========="
        )
        print(
            "Query:",
            repr(query)
        )
        print(
            "Intent:",
            intent
        )
        print(
            "IS numbers:",
            is_numbers
        )

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

            semantic = self.semantic_search(
                query,
                semantic_limit
            )

            exact = self.exact_standards(
                is_numbers
            )

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

        result = {
            "query": query,
            "intent": intent,
            "is_numbers": is_numbers,
            "semantic": semantic,
            "exact_standards": exact,
            "qco": qco,
            "labs": labs,
            "tests": tests,
        }

        print(
            "Semantic results:",
            len(semantic)
        )

        print(
            "Exact standards:",
            len(exact)
        )

        print(
            "QCO results:",
            len(qco)
        )

        print(
            "Lab results:",
            len(labs)
        )

        print(
            "Test results:",
            len(tests)
        )

        print(
            "========== HYBRID SEARCH COMPLETE =========="
        )
        print()

        return result


# ============================================================
# GLOBAL RETRIEVER
# ============================================================

try:

    hybrid_retriever = HybridRetriever()

except Exception as e:

    print(
        "Hybrid retriever initialization failed:",
        repr(e)
    )

    traceback.print_exc()

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

    test_query = (
        "Which BIS standard applies to composite cement?"
    )

    print()
    print("AUTOMATIC TEST:")
    print(test_query)
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
    print("Interactive mode")
    print("Type 'exit' to quit.")
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
        print("=== INTENT ===")
        print(result["intent"])

        print()
        print("=== IS NUMBERS ===")
        print(result["is_numbers"])

        print()
        print("=== STANDARDS ===")

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
        print("=== SEMANTIC RESULTS ===")

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
        print("=== QCO ===")

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
        print("=== LABS ===")

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
        print("=== TESTS ===")

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