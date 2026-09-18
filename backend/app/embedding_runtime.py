import json
import os
import threading
import unicodedata
from pathlib import Path

import numpy as np
from onnxruntime import ExecutionMode, InferenceSession, SessionOptions


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_LOCAL_PATH = BASE_DIR / "models" / "paraphrase-multilingual-MiniLM-L12-v2"
ONNX_MODEL_PATH = MODEL_LOCAL_PATH / "model.int8.onnx"
TOKENIZER_PATH = MODEL_LOCAL_PATH / "runtime_unigram_vocab.json"
CONFIG_PATH = MODEL_LOCAL_PATH / "config.json"
EMBEDDING_DIMENSIONS = 384
MAX_SEQUENCE_LENGTH = 128


class LocalOnnxEmbedder:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._session = None
        self._vocabulary = None
        self._max_sequence_length = MAX_SEQUENCE_LENGTH

    @classmethod
    def get(cls):
        if cls._instance is not None:
            return cls._instance

        with cls._lock:
            if cls._instance is None:
                instance = cls()
                instance._load()
                cls._instance = instance

        return cls._instance

    def _load(self):
        missing = [
            str(path)
            for path in (ONNX_MODEL_PATH, TOKENIZER_PATH, CONFIG_PATH)
            if not path.is_file()
        ]
        if missing:
            raise RuntimeError(
                "Local ONNX embedding assets are missing: "
                + ", ".join(missing)
                + ". Run scripts/prepare_embedding_runtime.py during the build."
            )

        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)

        hidden_size = int(config.get("hidden_size", 0))
        if hidden_size != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                "Embedding model dimension mismatch: "
                f"expected {EMBEDDING_DIMENSIONS}, got {hidden_size}."
            )

        with TOKENIZER_PATH.open("r", encoding="utf-8") as file:
            vocabulary = json.load(file)

        self._vocabulary = {
            item[0]: (int(item[1]), float(item[2]))
            for item in vocabulary
        }

        options = SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ExecutionMode.ORT_SEQUENTIAL
        options.enable_mem_pattern = True
        options.enable_cpu_mem_arena = False
        options.add_session_config_entry("session.disable_prepacking", "1")

        self._session = InferenceSession(
            str(ONNX_MODEL_PATH),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

        output_shape = self._session.get_outputs()[0].shape
        if output_shape[-1] != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                "ONNX embedding output dimension mismatch: "
                f"expected {EMBEDDING_DIMENSIONS}, got {output_shape[-1]}."
            )

        print("Embedding backend: ONNX Runtime CPU INT8")
        print("Embedding model path:", ONNX_MODEL_PATH)
        print("Embedding output dimensions:", EMBEDDING_DIMENSIONS)
        print("Memory-efficient runtime: enabled")

    def encode(self, text: str) -> list[float]:
        if self._session is None or self._vocabulary is None:
            raise RuntimeError("ONNX embedding runtime is not initialized.")

        token_ids = self._tokenize(text)
        inputs = {
            "input_ids": np.asarray([token_ids], dtype=np.int64),
            "attention_mask": np.ones((1, len(token_ids)), dtype=np.int64),
            "token_type_ids": np.zeros((1, len(token_ids)), dtype=np.int64),
        }

        token_embeddings = self._session.run(None, inputs)[0]
        attention_mask = inputs["attention_mask"].astype(np.float32)[..., None]
        pooled = (token_embeddings * attention_mask).sum(axis=1)
        pooled /= np.clip(attention_mask.sum(axis=1), 1e-9, None)

        norm = np.linalg.norm(pooled, axis=1, keepdims=True)
        normalized = pooled / np.clip(norm, 1e-12, None)
        vector = normalized[0].astype(np.float32).tolist()

        if len(vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                "Query embedding dimension mismatch: "
                f"expected {EMBEDDING_DIMENSIONS}, got {len(vector)}."
            )

        return vector

    def _tokenize(self, text: str) -> list[int]:
        normalized = unicodedata.normalize("NFKC", text or "")
        normalized = "▁" + normalized.replace(" ", "▁")
        pieces = self._unigram_pieces(normalized)
        token_ids = [0]
        token_ids.extend(pieces)
        token_ids.append(2)
        return token_ids[: self._max_sequence_length]

    def _unigram_pieces(self, text: str) -> list[int]:
        best = [None] * (len(text) + 1)
        best[0] = (0.0, [])

        for start in range(len(text)):
            if best[start] is None:
                continue

            current_score, current_ids = best[start]
            for end in range(start + 1, len(text) + 1):
                candidate = text[start:end]
                entry = self._vocabulary.get(candidate)
                if entry is None:
                    continue

                token_id, score = entry
                total_score = current_score + score
                previous = best[end]
                if previous is None or total_score > previous[0]:
                    best[end] = (total_score, current_ids + [token_id])

        if best[-1] is not None:
            return best[-1][1]

        return [3]


def load_embedding_model():
    return LocalOnnxEmbedder.get()