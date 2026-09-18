import os
import json
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "paraphrase-multilingual-MiniLM-L12-v2"
UNQUANTIZED_PATH = MODEL_DIR / "model.onnx"
QUANTIZED_PATH = MODEL_DIR / "model.int8.onnx"
RUNTIME_TOKENIZER_PATH = MODEL_DIR / "runtime_unigram_vocab.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EXPECTED_DIMENSIONS = 384


class TransformerOutput(torch.nn.Module):
    def __init__(self, transformer):
        super().__init__()
        self.transformer = transformer

    def forward(self, input_ids, attention_mask, token_type_ids):
        return self.transformer(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        ).last_hidden_state


def main():
    if not MODEL_DIR.is_dir():
        print("Downloading the build-time model:", MODEL_NAME)
        model = SentenceTransformer(MODEL_NAME, device="cpu")
        model.save(str(MODEL_DIR))
    else:
        print("Using existing local model:", MODEL_DIR)
        model = SentenceTransformer(
            str(MODEL_DIR),
            device="cpu",
            local_files_only=True,
        )

    transformer = model[0].auto_model.eval()
    hidden_size = int(transformer.config.hidden_size)
    if hidden_size != EXPECTED_DIMENSIONS:
        raise RuntimeError(
            f"Expected {EXPECTED_DIMENSIONS}-D model, got {hidden_size}."
        )

    tokenizer = model.tokenizer
    tokenizer_json = MODEL_DIR / "tokenizer.json"
    with tokenizer_json.open("r", encoding="utf-8") as file:
        tokenizer_data = json.load(file)

    runtime_vocabulary = [
        [token, index, score]
        for index, (token, score) in enumerate(tokenizer_data["model"]["vocab"])
    ]
    with RUNTIME_TOKENIZER_PATH.open("w", encoding="utf-8") as file:
        json.dump(runtime_vocabulary, file, ensure_ascii=False, separators=(",", ":"))

    sample = tokenizer(
        ["What are the relevant BIS standards for steel?"],
        padding="max_length",
        truncation=True,
        max_length=128,
        return_tensors="pt",
    )
    inputs = (
        sample["input_ids"],
        sample["attention_mask"],
        sample.get("token_type_ids", torch.zeros_like(sample["input_ids"])),
    )

    wrapper = TransformerOutput(transformer)
    with torch.no_grad():
        torch.onnx.export(
            wrapper,
            inputs,
            str(UNQUANTIZED_PATH),
            input_names=["input_ids", "attention_mask", "token_type_ids"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "sequence"},
                "attention_mask": {0: "batch", 1: "sequence"},
                "token_type_ids": {0: "batch", 1: "sequence"},
                "last_hidden_state": {0: "batch", 1: "sequence"},
            },
            opset_version=17,
            dynamo=False,
            do_constant_folding=True,
        )

    quantize_dynamic(
        str(UNQUANTIZED_PATH),
        str(QUANTIZED_PATH),
        weight_type=QuantType.QUInt8,
        per_channel=True,
        reduce_range=True,
    )
    UNQUANTIZED_PATH.unlink()

    if not QUANTIZED_PATH.is_file():
        raise RuntimeError("ONNX INT8 model conversion did not produce an output.")

    print("Prepared ONNX Runtime CPU INT8 model:", QUANTIZED_PATH)
    print("Embedding dimensions:", EXPECTED_DIMENSIONS)


if __name__ == "__main__":
    main()