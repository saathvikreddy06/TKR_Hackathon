import json
from pathlib import Path

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_admin
from app.firebase import db
from app.services.common import document_data
from app.routes.consultancies import safe_consultant_data


router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================
# PROJECT DATA PATHS
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"

NORMALIZED_DIR = DATA_DIR / "normalized"
PROCESSED_DIR = DATA_DIR / "processed"

STANDARDS_DIR = NORMALIZED_DIR / "standards"
LABS_DIR = NORMALIZED_DIR / "labs"
QCO_DIR = NORMALIZED_DIR / "qco"

STANDARDS_MASTER_FILE = (
    STANDARDS_DIR / "bis_standards_master.json"
)

STANDARDS_CATALOGUE_FILE = (
    STANDARDS_DIR / "bis_standards_catalogue.json"
)

STANDARD_DETAILS_FILE = (
    STANDARDS_DIR / "bis_standards_details.json"
)

QCO_LINKS_FILE = (
    STANDARDS_DIR / "standard_qco_links.json"
)

STANDARD_LAB_TEST_LINKS_FILE = (
    STANDARDS_DIR / "standard_lab_test_links.json"
)

LIMS_LABS_FILE = (
    LABS_DIR / "bis_lims_labs.json"
)

LIMS_TESTS_FILE = (
    LABS_DIR / "bis_lims_tests.json"
)

LIMS_CAPABILITIES_FILE = (
    LABS_DIR / "bis_lims_capabilities.json"
)

KNOWLEDGE_DOCUMENTS_FILE = (
    PROCESSED_DIR / "knowledge_documents.json"
)

KNOWLEDGE_CHUNKS_FILE = (
    PROCESSED_DIR / "knowledge_chunks.json"
)

EMBEDDING_CHUNKS_FILE = (
    PROCESSED_DIR / "embedding_chunks.json"
)

LOCAL_EMBEDDINGS_FILE = (
    PROCESSED_DIR / "local_knowledge_embeddings.jsonl"
)


# ============================================================
# GENERIC HELPERS
# ============================================================

def all_documents(collection: str):
    return [
        document_data(document)
        for document in db.collection(collection).stream()
    ]


def load_json(path: Path):
    if not path.exists():
        return None

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):
        return None


def count_json_records(path: Path):
    data = load_json(path)

    if data is None:
        return None

    if isinstance(data, list):
        return len(data)

    if isinstance(data, dict):
        for key in (
            "links",
            "standards",
            "documents",
            "chunks",
            "records",
            "tests",
            "capabilities",
            "labs",
            "events",
            "states",
        ):
            value = data.get(key)

            if isinstance(value, list):
                return len(value)

    return None


def count_jsonl_records(path: Path):
    if not path.exists():
        return None

    count = 0

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:
                if line.strip():
                    count += 1

        return count

    except OSError:
        return None


def first_available_count(*paths):
    for path in paths:
        count = count_json_records(path)

        if count is not None:
            return count

    return None


# ============================================================
# QCO DATA HELPERS
# ============================================================

def find_qco_events_count():
    candidates = [
        QCO_DIR / "qco_events.json",
        QCO_DIR / "bis_qco_events.json",
        QCO_DIR / "normalized_qco_events.json",
        QCO_DIR / "qco_event_records.json",
    ]

    count = first_available_count(*candidates)

    if count is not None:
        return count

    return None


def find_qco_states_count():
    candidates = [
        QCO_DIR / "qco_states.json",
        QCO_DIR / "bis_qco_states.json",
        QCO_DIR / "normalized_qco_states.json",
        QCO_DIR / "is_qco_states.json",
    ]

    count = first_available_count(*candidates)

    if count is not None:
        return count

    return None


# ============================================================
# FIRESTORE HELPERS
# ============================================================

def firestore_collection_count(collection: str):
    return len(
        list(
            db.collection(collection).stream()
        )
    )


def firestore_consultant_count():
    return len(
        list(
            db.collection("users")
            .where(
                "role",
                "==",
                "consultant"
            )
            .stream()
        )
    )


# ============================================================
# CONSULTANTS
# ============================================================

@router.get("/consultants")
def admin_consultants(
    current_user=Depends(require_admin)
):

    consultants = []

    for document in (
        db.collection("users")
        .where(
            "role",
            "==",
            "consultant"
        )
        .stream()
    ):

        data = document_data(document)

        safe_data = safe_consultant_data(
            data
        )

        safe_data["created_at"] = (
            data.get("created_at")
        )

        safe_data["updated_at"] = (
            data.get("updated_at")
        )

        consultants.append(
            safe_data
        )

    return {
        "consultants": consultants
    }


# ============================================================
# CONSULTATIONS
# ============================================================

@router.get("/consultations")
def admin_consultations(
    current_user=Depends(require_admin)
):

    return {
        "consultations": all_documents(
            "consultation_requests"
        )
    }


# ============================================================
# FEEDBACK
# ============================================================

@router.get("/feedback")
def admin_feedback(
    current_user=Depends(require_admin)
):

    return {
        "feedback": all_documents(
            "feedback"
        )
    }


# ============================================================
# ADMIN STATISTICS
# ============================================================

@router.get("/stats")
def admin_stats(
    current_user=Depends(require_admin)
):

    # --------------------------------------------------------
    # Firestore platform statistics
    # --------------------------------------------------------

    stats = {
        "consultations": firestore_collection_count(
            "consultation_requests"
        ),

        "chat_sessions": firestore_collection_count(
            "chat_sessions"
        ),

        "feedback": firestore_collection_count(
            "feedback"
        ),

        "search_history": firestore_collection_count(
            "search_history"
        ),

        "consultants": firestore_consultant_count(),
    }


    # --------------------------------------------------------
    # BIS Standards
    # --------------------------------------------------------

    standards_count = count_json_records(
        STANDARDS_MASTER_FILE
    )

    if standards_count is None:
        standards_count = count_json_records(
            STANDARDS_CATALOGUE_FILE
        )

    stats["standards"] = (
        standards_count
    )


    # --------------------------------------------------------
    # BIS LIMS laboratories
    # --------------------------------------------------------

    stats["labs"] = count_json_records(
        LIMS_LABS_FILE
    )


    # --------------------------------------------------------
    # BIS LIMS tests
    #
    # This represents the normalized test records used
    # directly by the current RAG retriever.
    # --------------------------------------------------------

    stats["lims_tests"] = count_json_records(
        LIMS_TESTS_FILE
    )


    # --------------------------------------------------------
    # BIS LIMS capabilities
    # --------------------------------------------------------

    stats["lims_capabilities"] = count_json_records(
        LIMS_CAPABILITIES_FILE
    )


    # --------------------------------------------------------
    # QCO relationships
    # --------------------------------------------------------

    qco_links_count = count_json_records(
        QCO_LINKS_FILE
    )

    stats["qco_links"] = (
        qco_links_count
    )


    # --------------------------------------------------------
    # QCO events
    # --------------------------------------------------------

    stats["qco_events"] = (
        find_qco_events_count()
    )


    # --------------------------------------------------------
    # IS-QCO states
    # --------------------------------------------------------

    stats["qco_states"] = (
        find_qco_states_count()
    )


    # --------------------------------------------------------
    # Standard → Lab → Test relationships
    # --------------------------------------------------------

    stats["testing_links"] = (
        count_json_records(
            STANDARD_LAB_TEST_LINKS_FILE
        )
    )


    # --------------------------------------------------------
    # Knowledge documents
    # --------------------------------------------------------

    stats["knowledge_documents"] = (
        count_json_records(
            KNOWLEDGE_DOCUMENTS_FILE
        )
    )


    # --------------------------------------------------------
    # Knowledge chunks
    # --------------------------------------------------------

    stats["knowledge_chunks"] = (
        count_json_records(
            KNOWLEDGE_CHUNKS_FILE
        )
    )


    # --------------------------------------------------------
    # Embedding chunks
    # --------------------------------------------------------

    stats["embedding_chunks"] = (
        count_json_records(
            EMBEDDING_CHUNKS_FILE
        )
    )


    # --------------------------------------------------------
    # Local embeddings
    # --------------------------------------------------------

    local_embeddings = count_jsonl_records(
        LOCAL_EMBEDDINGS_FILE
    )

    embedding_chunks = (
        stats["embedding_chunks"]
    )

    stats["local_embeddings"] = {
        "completed": local_embeddings,
        "total": embedding_chunks,
    }


    # --------------------------------------------------------
    # Firebase embeddings
    #
    # Firestore collection currently used by the RAG uploader.
    # --------------------------------------------------------

    firebase_embedding_count = (
        firestore_collection_count(
            "standard_chunks_local"
        )
    )

    stats["firebase_embeddings"] = {
        "completed": firebase_embedding_count,
        "total": embedding_chunks,
    }


    # --------------------------------------------------------
    # Overall pipeline health
    # --------------------------------------------------------

    stats["pipeline"] = {
        "standards_loaded": (
            standards_count is not None
        ),

        "labs_loaded": (
            stats["labs"] is not None
        ),

        "lims_tests_loaded": (
            stats["lims_tests"] is not None
        ),

        "qco_links_loaded": (
            stats["qco_links"] is not None
        ),

        "testing_links_loaded": (
            stats["testing_links"] is not None
        ),

        "knowledge_documents_loaded": (
            stats["knowledge_documents"] is not None
        ),

        "knowledge_chunks_loaded": (
            stats["knowledge_chunks"] is not None
        ),

        "local_embeddings_complete": (
            local_embeddings is not None
            and embedding_chunks is not None
            and local_embeddings >= embedding_chunks
        ),

        "firebase_embeddings_complete": (
            firebase_embedding_count is not None
            and embedding_chunks is not None
            and firebase_embedding_count >= embedding_chunks
        ),
    }


    return stats