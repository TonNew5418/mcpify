"""
Embedding providers for semantic function matching.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Union

import numpy as np


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def encode(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Encode text(s) into embeddings.

        Args:
            texts: Single text or list of texts to encode
            **kwargs: Provider-specific arguments

        Returns:
            Numpy array of embeddings with shape (n_texts, embedding_dim)
        """
        pass

    @abstractmethod
    def compute_similarity(
        self, query_embedding: np.ndarray, doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute similarity scores between query and document embeddings.

        Args:
            query_embedding: Query embedding of shape (embedding_dim,)
            doc_embeddings: Document embeddings of shape (n_docs, embedding_dim)

        Returns:
            Similarity scores of shape (n_docs,)
        """
        pass


class SentenceTransformersProvider(EmbeddingProvider):
    """Sentence-Transformers based embedding provider."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with specified model.

        Args:
            model_name: HuggingFace model name for sentence-transformers
        """
        try:
            from sentence_transformers import SentenceTransformer, util

            self.model = SentenceTransformer(model_name)
            self.util = util
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for SentenceTransformersProvider. "
                "Install with: pip install sentence-transformers"
            ) from None

    def encode(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Encode texts using sentence-transformers."""
        if isinstance(texts, str):
            texts = [texts]

        # Convert to tensor and then to numpy for consistency
        embeddings = self.model.encode(texts, convert_to_tensor=True, **kwargs)
        return embeddings.cpu().numpy()

    def compute_similarity(
        self, query_embedding: np.ndarray, doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity using sentence-transformers util."""
        import torch

        # Convert numpy arrays back to tensors for sentence-transformers util
        query_tensor = torch.from_numpy(query_embedding)
        doc_tensor = torch.from_numpy(doc_embeddings)

        # Compute cosine similarity
        similarities = self.util.cos_sim(query_tensor, doc_tensor)[0]
        return similarities.cpu().numpy()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embeddings API provider."""

    def __init__(
        self, model_name: str = "text-embedding-3-small", api_key: Optional[str] = None
    ):
        """Initialize OpenAI embedding provider.

        Args:
            model_name: OpenAI embedding model name
            api_key: OpenAI API key (if None, will use environment variable)
        """
        try:
            import openai

            if api_key:
                openai.api_key = api_key
            self.client = openai.OpenAI()
            self.model_name = model_name
        except ImportError:
            raise ImportError(
                "openai is required for OpenAIEmbeddingProvider. "
                "Install with: pip install openai"
            ) from None

    def encode(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Encode texts using OpenAI embeddings API."""
        if isinstance(texts, str):
            texts = [texts]

        response = self.client.embeddings.create(model=self.model_name, input=texts)

        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings)

    def compute_similarity(
        self, query_embedding: np.ndarray, doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity manually."""
        # Normalize embeddings
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(
            doc_embeddings, axis=1, keepdims=True
        )

        # Compute cosine similarity
        similarities = np.dot(doc_norms, query_norm)
        return similarities


def create_embedding_provider(
    provider_type: str = "sentence_transformers", **kwargs
) -> EmbeddingProvider:
    """Factory function to create embedding providers.

    Args:
        provider_type: Type of provider ('sentence_transformers', 'openai')
        **kwargs: Provider-specific arguments

    Returns:
        Embedding provider instance
    """
    if provider_type == "sentence_transformers":
        return SentenceTransformersProvider(**kwargs)
    elif provider_type == "openai":
        return OpenAIEmbeddingProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
