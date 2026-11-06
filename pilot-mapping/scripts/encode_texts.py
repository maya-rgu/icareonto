#!/usr/bin/env python3
"""Offline embedding worker; can run in a separate existing ML environment."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args()
    # No remote code or model downloads; all inference is local and on CPU.
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    import torch
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(2)
    request = json.loads(args.request.read_text())
    model = SentenceTransformer(str(args.model_dir), local_files_only=True, trust_remote_code=False, device="cpu")
    model.eval()
    # Detect lost text explicitly: the caller rejects any silent model truncation.
    token_lengths = [len(ids) for ids in model.tokenizer(request["texts"], truncation=False)["input_ids"]]
    vectors = model.encode(request["texts"], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
    # Record the actual local weights and configuration used to produce the vectors.
    relevant = {"model.safetensors", "pytorch_model.bin", "config.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt", "special_tokens_map.json", "modules.json", "sentence_bert_config.json", "config_sentence_transformers.json"}
    files = {}
    for path in sorted(args.model_dir.rglob("*")):
        if path.is_file() and (path.name in relevant or path.parent.name == "1_Pooling"):
            files[str(path.relative_to(args.model_dir))] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {
        "vectors": vectors.tolist(), "dimensions": int(vectors.shape[1]),
        "model_max_seq_length": model.max_seq_length,
        "truncated_text_indices": [i for i, n in enumerate(token_lengths) if n > model.max_seq_length],
        "device": "cpu", "normalised": True, "model_files_sha256": files,
        "versions": {name: importlib.metadata.version(name) for name in ("sentence-transformers", "torch", "transformers", "numpy")}
    }
    args.output.write_text(json.dumps(result))


if __name__ == "__main__":
    main()
