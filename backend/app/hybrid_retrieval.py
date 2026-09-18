import json
import os
import re
import math
import threading
import traceback
from collections import defaultdict

from app.firebase import db
from app.embedding_runtime import load_embedding_model
from app.structured_lookup import StructuredLookupIndex


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

LIMS_LABS_PATH = os.path.join(
    LIMS_TESTS_DIR,
    "bis_lims_labs.json"
)

STRUCTURED_LIMS_INDEX_PATH = os.path.join(
    PROCESSED_DIR,
    "structured_lims_lookup.sqlite3"
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
    pattern = re.compile(
        r"\b(?:I\.S\.?|IS|IEC(?:\s*/\s*IS)?)\s*"
        r"(?:NO\.?\s*)?(\d{3,6})"
        r"(?:\s*\(??\s*(?:PART|PT)\s*[-./]?\s*(\d{1,3})\s*\)??)?"
        r"(?:\s*[:/-]?\s*(\d{4}))?",
        re.IGNORECASE,
    )

    identifiers = []
    for match in pattern.finditer(query or ""):
        number, part, year = match.groups()
        value = f"IS {number}"
        if part:
            value += f" Part {part}"
        if year:
            value += f":{year}"
        if value not in identifiers:
            identifiers.append(value)

    return identifiers


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
        self.standards_by_base = defaultdict(list)
        self.standards_by_title = []

        self.qco_links = []
        self.qco_by_number = defaultdict(list)
        self.qco_by_base = defaultdict(list)
        self.qco_status = "not_found"
        self.qco_error = None

        self.lims_tests_path = LIMS_TESTS_PATH
        self.structured_lims = StructuredLookupIndex(
            LIMS_TESTS_PATH,
            LIMS_LABS_PATH,
            STRUCTURED_LIMS_INDEX_PATH,
        )

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

                base_key = self._normalize_is_base(number)
                if base_key:
                    self.standards_by_base[base_key].append(item)

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

            self.qco_status = "error"
            self.qco_error = "QCO relationship dataset is unavailable."

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
            self.qco_status = "supported" if data else "not_found"

            for item in data:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                values = item.get("matched_is_numbers") or []
                values = list(values) if isinstance(values, list) else [values]
                values.append(
                    item.get("standard_number")
                    or item.get("is_number")
                    or item.get("standard_id")
                )

                for number in values:
                    if not number:
                        continue

                    for normalized in self._identifier_keys(number):
                        self.qco_by_number[normalized].append(item)

                    base_key = self._normalize_is_base(number)
                    if base_key:
                        self.qco_by_base[base_key].append(item)

        except Exception as e:

            print(
                "QCO loading error:",
                repr(e)
            )

            traceback.print_exc()

            self.qco_links = []
            self.qco_status = "error"
            self.qco_error = f"{type(e).__name__}: {e}"

    # ========================================================
    # LOAD LIMS TESTS
    # ========================================================

    def _load_lims_tests(self):
        if os.path.isfile(self.lims_tests_path):
            print("LIMS tests: indexed lookup enabled")
        else:
            print("LIMS tests file not found:", self.lims_tests_path)

    # ========================================================
    # IS NUMBER NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_is_number(
        value
    ):
        keys = StructuredLookupIndex.identifier_keys(value)
        return StructuredLookupIndex.primary_key(value) if keys else ""

    @staticmethod
    def _normalize_is_base(value):
        keys = StructuredLookupIndex.identifier_keys(value)
        if not keys:
            return ""
        return min(keys, key=lambda key: (key.count(":"), len(key)))

    @staticmethod
    def _identifier_keys(value):
        return StructuredLookupIndex.identifier_keys(value)

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

                if not result["standard_number"]:
                    extracted = extract_is_numbers(result["text"])
                    if extracted:
                        result["standard_number"] = extracted[0]

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
        seen = set()

        for number in is_numbers:
            keys = self._identifier_keys(number)
            base_key = self._normalize_is_base(number)
            candidate_items = []
            for key in keys:
                candidate_items.extend(self.standards_by_number.get(key, []))
            if base_key:
                candidate_items.extend(self.standards_by_base.get(base_key, []))

            for item in candidate_items:
                identity = (
                    item.get("standard_id")
                    or item.get("document_id")
                    or item.get("standard_number")
                    or id(item)
                )
                if identity in seen:
                    continue
                seen.add(identity)
                result = dict(item)
                result["match_type"] = "exact_standard"
                results.append(result)

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

        stop_words = {
            "bis",
            "standard",
            "standards",
            "indian",
            "on",
            "for",
            "the",
            "and",
            "of",
            "related",
            "test",
            "tests",
            "testing",
            "laboratory",
            "laboratories",
            "lab",
            "required",
            "requirements",
        }
        query_tokens = {
            token
            for token in normalized_query.split()
            if token not in stop_words
        }

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
            keys = self._identifier_keys(number)
            base_key = self._normalize_is_base(number)
            candidate_items = []
            for key in keys:
                candidate_items.extend(self.qco_by_number.get(key, []))
            if base_key:
                candidate_items.extend(self.qco_by_base.get(base_key, []))

            for item in candidate_items:
                result = dict(item)
                result["match_type"] = "qco_relationship"
                results.append(result)

        return self._deduplicate_results(
            results
        )

    def qco_product_search(self, query, limit=30):
        terms = {
            token
            for token in normalize_search_text(query).split()
            if len(token) > 2
            and token not in {
                "bis", "qco", "quality", "control", "order",
                "orders", "for", "the", "and", "related", "on",
            }
        }
        if not terms:
            return []

        scored = []
        for item in self.qco_links:
            standard_number = item.get("standard_number") or ""
            standard_items = self.standards_by_number.get(
                self._normalize_is_number(standard_number), []
            )
            title = " ".join(
                str(standard.get("title") or "")
                for standard in standard_items
            )
            evidence = " ".join(
                str(item.get(field) or "")
                for field in ("relationship", "evidence", "product", "category")
            )
            haystack = normalize_search_text(f"{title} {evidence}")
            overlap = len(terms & set(haystack.split()))
            if overlap:
                result = dict(item)
                result["match_type"] = "qco_relationship"
                scored.append((overlap, result))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return self._deduplicate_results(
            [item for _, item in scored[:limit]]
        )

    def lims_search(self, is_numbers, test_limit=50, lab_limit=20):
        """Return verified LIMS tests and laboratories for standard identifiers."""
        return self.structured_lims.lookup(
            is_numbers,
            test_limit=test_limit,
            lab_limit=lab_limit,
        )

    # ========================================================
    # LAB SEARCH
    # ========================================================

    def lab_search(
        self,
        is_numbers,
        limit=20
    ):

        indexed = self.lims_search(
            is_numbers,
            test_limit=max(limit, 50),
            lab_limit=limit,
        )
        return indexed.get("laboratories", [])

    # ========================================================
    # TEST SEARCH
    # ========================================================

    def test_search(
        self,
        is_numbers,
        limit=50
    ):

        indexed = self.lims_search(
            is_numbers,
            test_limit=limit,
            lab_limit=20,
        )
        return indexed.get("tests", [])

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

        # Retrieve general BIS knowledge for every in-scope intent. The
        # structured lookups below remain deterministic and evidence-backed.
        discovery_limit = max(int(semantic_limit), 20)
        keyword_limit = max(int(semantic_limit), 50)
        semantic = self.semantic_search(
            query,
            discovery_limit
        )

        exact = self.exact_standards(
            is_numbers
        )

        if not is_numbers:
            exact.extend(
                self.standard_keyword_search(
                    query,
                    keyword_limit
                )
            )
        exact = self._deduplicate_results(exact)

        lookup_identifiers = list(is_numbers)
        if not is_numbers:
            for item in exact + semantic:
                identifier = (
                    item.get("standard_number")
                    or item.get("is_number")
                    or (item.get("metadata") or {}).get("standard_number")
                    or (item.get("metadata") or {}).get("is_number")
                )
                if identifier and identifier not in lookup_identifiers:
                    lookup_identifiers.append(identifier)

        qco = self.qco_search(lookup_identifiers)
        if not is_numbers and intent == "qco":
            qco.extend(self.qco_product_search(query))
            qco = self._deduplicate_results(qco)
        lims = self.lims_search(
            lookup_identifiers,
            test_limit=50,
            lab_limit=lab_limit,
        )
        tests = lims.get("tests", [])
        labs = lims.get("laboratories", [])

        result = {
            "query": query,
            "intent": intent,
            "is_numbers": is_numbers,
            "semantic": semantic,
            "exact_standards": exact,
            "qco": qco,
            "labs": labs,
            "tests": tests,
            "standards": exact,
            "knowledge": semantic,
            "laboratories": labs,
            "qcos": qco,
            "structured_status": lims.get("status", "not_found"),
            "structured_error": lims.get("error"),
            "qco_status": self.qco_status,
            "qco_error": self.qco_error,
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
            "standards": [],
            "knowledge": [],
            "laboratories": [],
            "qcos": [],
            "structured_status": "error",
            "structured_error": "Hybrid retriever is unavailable.",
            "qco_status": "error",
            "qco_error": "Hybrid retriever is unavailable.",
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