import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from rag_service.domain.models import (
    Chunk,
    DocumentType,
    LLMResponse,
    Message,
    MessageRole,
    ServiceMetadata,
)
from rag_service.pipeline.rag_engine import MAX_HISTORY_MESSAGES, RAGPipeline


class TestConversationalRetrieval(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_vector_store = MagicMock()
        self.mock_vector_store.search = AsyncMock(return_value=[
            Chunk(
                id="chunk-1",
                content="PersonalVehicleHandler handles FOUR_WHEELER_PERSONAL flow and calls AssessmentEngine.",
                metadata=ServiceMetadata(
                    file_path="PersonalVehicleHandler.kt",
                    document_type=DocumentType.SOURCE_CODE,
                    source="repository",
                    class_name="PersonalVehicleHandler",
                    method_name="assess",
                    service="income-assessment-service",
                ),
            )
        ])

        self.mock_embedding_provider = MagicMock()
        self.mock_embedding_provider.embed_query = AsyncMock(return_value=[0.1] * 384)

        self.mock_llm_provider = MagicMock()
        self.mock_llm_provider.generate = AsyncMock(
            return_value=LLMResponse(
                content="Grounded answer to the question",
                model="test-model",
                provider="test-provider",
            )
        )
        self.mock_llm_provider.stream = MagicMock(return_value=iter(["streamed chunk"]))

        self.mock_prompt_loader = MagicMock()
        self.mock_prompt_loader.render = MagicMock(
            side_effect=lambda name, **kwargs: f"Rendered [{name}] with {kwargs}"
        )

        self.pipeline = RAGPipeline(
            vector_store=self.mock_vector_store,
            embedding_provider=self.mock_embedding_provider,
            llm_provider=self.mock_llm_provider,
            prompt_loader=self.mock_prompt_loader,
            default_service="income-assessment-service",
            max_history_messages=6,
        )

    async def test_single_turn_no_history_skips_llm_rewrite(self):
        """When chat_history is empty, query_text is embedded directly without extra LLM call."""
        result = await self.pipeline.query(
            query_text="What is Zenith?",
            service="income-assessment-service",
            chat_history=None,
        )

        # Embedding should be called with original query
        self.mock_embedding_provider.embed_query.assert_awaited_once_with("What is Zenith?")
        # LLM generate should only be called once (for final answer, not rewrite)
        self.assertEqual(self.mock_llm_provider.generate.await_count, 1)
        self.assertEqual(result.answer, "Grounded answer to the question")

    async def test_multi_turn_triggers_standalone_query_rewriting(self):
        """When chat_history is provided, standalone query is generated and embedded."""
        history = [
            Message(role=MessageRole.USER, content="Explain the FOUR_WHEELER_PERSONAL flow."),
            Message(role=MessageRole.ASSISTANT, content="It is handled by PersonalVehicleHandler."),
        ]

        # Return rewritten query on first call, final answer on second call
        self.mock_llm_provider.generate = AsyncMock(side_effect=[
            LLMResponse(
                content="What downstream components does PersonalVehicleHandler call for FOUR_WHEELER_PERSONAL?",
                model="test-model",
                provider="test-provider",
            ),
            LLMResponse(
                content="PersonalVehicleHandler calls AssessmentEngine.",
                model="test-model",
                provider="test-provider",
            ),
        ])

        result = await self.pipeline.query(
            query_text="What does it call next?",
            service="income-assessment-service",
            chat_history=history,
        )

        # Vector store embedding must receive the rewritten standalone query
        self.mock_embedding_provider.embed_query.assert_awaited_once_with(
            "What downstream components does PersonalVehicleHandler call for FOUR_WHEELER_PERSONAL?"
        )

        # Vector search must use target service filter
        self.mock_vector_store.search.assert_awaited_once_with(
            query_vector=[0.1] * 384,
            limit=4,
            service_filter="income-assessment-service",
        )

        # Check prompt loader calls:
        # 1. query_rewrite rendered with history and follow-up query
        # 2. system prompt
        # 3. query_answer prompt rendered with the ORIGINAL query_text
        render_calls = self.mock_prompt_loader.render.call_args_list
        template_names = [call[0][0] for call in render_calls]
        self.assertIn("query_rewrite", template_names)
        self.assertIn("query_answer", template_names)

        # Verify query_answer received the raw original query_text
        answer_call_kwargs = [
            call[1] for call in render_calls if call[0][0] == "query_answer"
        ][0]
        self.assertEqual(answer_call_kwargs["query_str"], "What does it call next?")
        self.assertIn("User: Explain the FOUR_WHEELER_PERSONAL flow.", answer_call_kwargs["chat_history"])

    async def test_configurable_history_limit(self):
        """Pipeline respects custom max_history_messages."""
        pipeline_small = RAGPipeline(
            vector_store=self.mock_vector_store,
            embedding_provider=self.mock_embedding_provider,
            llm_provider=self.mock_llm_provider,
            prompt_loader=self.mock_prompt_loader,
            max_history_messages=2,
        )

        history = [
            Message(role=MessageRole.USER, content="Msg 1"),
            Message(role=MessageRole.ASSISTANT, content="Msg 2"),
            Message(role=MessageRole.USER, content="Msg 3"),
            Message(role=MessageRole.ASSISTANT, content="Msg 4"),
        ]

        self.mock_llm_provider.generate = AsyncMock(side_effect=[
            LLMResponse(content="Rewritten query", model="test-model", provider="test-provider"),
            LLMResponse(content="Final answer", model="test-model", provider="test-provider"),
        ])

        await pipeline_small.query(
            query_text="Follow up question",
            chat_history=history,
        )

        # Check that query_rewrite only received the last 2 messages (Msg 3 and Msg 4)
        rewrite_call_kwargs = [
            call[1] for call in self.mock_prompt_loader.render.call_args_list if call[0][0] == "query_rewrite"
        ][0]
        self.assertNotIn("Msg 1", rewrite_call_kwargs["chat_history"])
        self.assertNotIn("Msg 2", rewrite_call_kwargs["chat_history"])
        self.assertIn("Msg 3", rewrite_call_kwargs["chat_history"])
        self.assertIn("Msg 4", rewrite_call_kwargs["chat_history"])

    async def test_query_rewrite_failure_fallback(self):
        """If rewriting throws an exception, pipeline falls back gracefully to raw query."""
        history = [
            Message(role=MessageRole.USER, content="Prior context"),
            Message(role=MessageRole.ASSISTANT, content="Prior response"),
        ]

        # First call (rewrite) raises error, second call (answer) succeeds
        self.mock_llm_provider.generate = AsyncMock(side_effect=[
            RuntimeError("LLM API rate limit or error"),
            LLMResponse(content="Fallback answer", model="test", provider="test"),
        ])

        result = await self.pipeline.query(
            query_text="Fallback follow-up question",
            chat_history=history,
        )

        # Should fall back to embedding the original query
        self.mock_embedding_provider.embed_query.assert_awaited_once_with("Fallback follow-up question")
        self.assertEqual(result.answer, "Fallback answer")


if __name__ == "__main__":
    unittest.main()
