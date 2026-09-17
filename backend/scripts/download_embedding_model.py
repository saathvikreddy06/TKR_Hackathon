import os

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

MODEL_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "models",
    "paraphrase-multilingual-MiniLM-L12-v2",
)


def main():
    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    print("=" * 70)
    print("StandIQ embedding model preparation")
    print("=" * 70)

    print("Model:")
    print(MODEL_NAME)

    print("Target directory:")
    print(MODEL_DIR)

    print()
    print("Downloading/loading model during BUILD...")

    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu"
    )

    print()
    print("Saving model locally...")

    model.save(
        MODEL_DIR
    )

    print()
    print("Testing local model...")

    test_vector = model.encode(
        "IS 16415:2015",
        normalize_embeddings=True
    )

    dimensions = len(
        test_vector
    )

    print(
        "Test embedding dimensions:",
        dimensions
    )

    if dimensions != 384:

        raise RuntimeError(
            "Embedding dimension mismatch. "
            f"Expected 384, got {dimensions}."
        )

    print()
    print("Embedding model prepared successfully.")
    print("=" * 70)


if __name__ == "__main__":
    main()