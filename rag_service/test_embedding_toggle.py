import os
import unittest
from unittest.mock import patch

from rag_service.infrastructure.config import Settings
from rag_service.infrastructure.providers.gemini_embedding import GeminiEmbeddingProvider
from rag_service.infrastructure.providers.qdrant_embedding import QdrantEmbeddingProvider


class TestEmbeddingToggle(unittest.TestCase):
    def test_default_toggle_is_false(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("USE_LOCAL_JINA_EMBEDDINGS", None)
            settings = Settings()
            self.assertFalse(settings.use_local_jina_embeddings)

    def test_toggle_false_with_gemini_key_uses_gemini_delegate(self):
        with patch.dict(
            os.environ,
            {
                "USE_LOCAL_JINA_EMBEDDINGS": "false",
                "GEMINI_API_KEY": "AIzaSyTestValidGeminiKey12345",
            },
            clear=False,
        ):
            settings = Settings()
            self.assertFalse(settings.use_local_jina_embeddings)
            self.assertTrue(settings.has_valid_gemini_key())

            provider = QdrantEmbeddingProvider(settings)
            self.assertIsNotNone(provider._gemini_delegate)
            self.assertIsNone(provider._model)
            self.assertEqual(provider.dimension, 768)
            self.assertEqual(provider.model_name, "gemini-embedding-001")

    def test_gemini_embedding_provider_initialization(self):
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "AIzaSyTestValidGeminiKey12345",
                "GEMINI_EMBEDDING_MODEL_ID": "models/gemini-embedding-001",
            },
            clear=False,
        ):
            settings = Settings()
            provider = GeminiEmbeddingProvider(settings, dimension=768)
            self.assertEqual(provider.model_name, "gemini-embedding-001")
            self.assertEqual(provider.dimension, 768)


if __name__ == "__main__":
    unittest.main()

