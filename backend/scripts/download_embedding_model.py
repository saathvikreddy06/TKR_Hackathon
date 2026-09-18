"""Backward-compatible entry point for Render's model build step.

The production process uses the ONNX Runtime artifact, not the PyTorch model.
Keep this filename because older Render build commands already invoke it.
"""

from prepare_embedding_runtime import main


if __name__ == "__main__":
    main()