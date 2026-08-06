from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        # `model` stays the model *name*: langchain-style integrations (Ragas telemetry among
        # them) expect a string there. The loaded SentenceTransformer lives on `encoder`.
        self.model = model_name
        self.encoder = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.encoder.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.encoder.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()
