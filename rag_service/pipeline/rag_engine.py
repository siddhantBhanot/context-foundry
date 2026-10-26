import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from rag_service.domain.models import (
    Chunk,
    Message,
    MessageRole,
    QueryResult,
    SourceReference,
)
from rag_service.domain.protocols import EmbeddingProvider, LLMProvider, VectorStore
from rag_service.prompts.loader import PromptLoader, get_prompt_loader

logger = logging.getLogger("rag_service.pipeline")

MAX_HISTORY_MESSAGES: int = 6


class ContextAssembler:
    """
    Assembles retrieved chunks into structured context text and
    extracts verified source citations.
    """

    @staticmethod
    def assemble(chunks: List[Chunk]) -> Tuple[str, List[SourceReference]]:
        if not chunks:
            return "No matching documentation or source code found for the query.", []

        context_blocks: List[str] = []
        sources: List[SourceReference] = []
        seen_files = set()

        for idx, chunk in enumerate(chunks, start=1):
            meta = chunk.metadata
            file_ref = meta.file_path

            # Format source reference
            source = SourceReference(
                file=file_ref,
                service=meta.service,
                document_type=meta.document_type.value,
                class_name=meta.class_name,
                method_name=meta.method_name,
                endpoint=meta.endpoint,
                start_line=meta.start_line,
                end_line=meta.end_line,
                snippet=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            )
            if file_ref not in seen_files:
                sources.append(source)
                seen_files.add(file_ref)

            header_info = f"[Source {idx}: {file_ref}"
            if meta.class_name:
                header_info += f" | Class: {meta.class_name}"
            if meta.method_name:
                header_info += f" | Method: {meta.method_name}"
            if meta.endpoint:
                header_info += f" | Endpoint: {meta.endpoint}"
            header_info += "]"

            context_blocks.append(f"{header_info}\n{chunk.content}\n")

        return "\n---------------------\n".join(context_blocks), sources


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.
    Orchestrates query processing, metadata filtering, semantic retrieval,
    context assembly, prompt construction, and LLM generation.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        prompt_loader: Optional[PromptLoader] = None,
        default_service: str = "income-assessment-service",
        max_history_messages: int = MAX_HISTORY_MESSAGES,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        self.prompt_loader = prompt_loader or get_prompt_loader()
        self.default_service = default_service
        self.max_history_messages = max_history_messages
        self.context_assembler = ContextAssembler()

    async def _generate_standalone_query(
        self,
        query_text: str,
        service: str,
        chat_history: Optional[List[Message]],
    ) -> str:
        """
        Generate a standalone, search-optimized query from follow-up questions
        and recent conversation history to resolve pronouns and implicit references.
        """
        if not chat_history:
            return query_text

        recent_history = chat_history[-self.max_history_messages:]
        history_lines = [f"{m.role.value.capitalize()}: {m.content}" for m in recent_history]
        formatted_history = "\n".join(history_lines)

        try:
            rewrite_prompt = self.prompt_loader.render(
                "query_rewrite",
                service=service,
                chat_history=formatted_history,
                query_str=query_text,
            )
            messages = [Message(role=MessageRole.USER, content=rewrite_prompt)]
            system_prompt = (
                "You are an expert technical query reformulation assistant. "
                "Output only the standalone rewritten search query."
            )
            response = await self.llm_provider.generate(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.0,
            )
            rewritten = response.content.strip().strip('"\'')
            if rewritten:
                logger.debug(
                    "Rewrote conversational query '%s' -> '%s' for service '%s'",
                    query_text,
                    rewritten,
                    service,
                )
                return rewritten
            return query_text
        except Exception as e:
            logger.warning("Query rewrite failed, falling back to raw query: %s", e)
            return query_text

    async def query(
        self,
        query_text: str,
        service: Optional[str] = None,
        chat_history: Optional[List[Message]] = None,
        top_k: int = 4,
        temperature: float = 0.1,
        model: Optional[str] = None,
    ) -> QueryResult:
        """
        Execute full RAG query workflow with optional model selection.
        """
        start_time = time.perf_counter()
        target_service = service or self.default_service

        # 1. Generate standalone retrieval query for conversation-aware retrieval
        retrieval_query = await self._generate_standalone_query(
            query_text=query_text,
            service=target_service,
            chat_history=chat_history,
        )

        # 2. Embed standalone query
        query_vector = await self.embedding_provider.embed_query(retrieval_query)

        # 3. Retrieve with service-level filtering
        retrieved_chunks = await self.vector_store.search(
            query_vector=query_vector,
            limit=top_k,
            service_filter=target_service,
        )

        # 4. Assemble Context & Citations
        context_str, sources = self.context_assembler.assemble(retrieved_chunks)

        # 5. Format Conversation History using configurable limit
        formatted_history = ""
        if chat_history:
            history_lines = [
                f"{m.role.value.capitalize()}: {m.content}"
                for m in chat_history[-self.max_history_messages:]
            ]
            formatted_history = "\n".join(history_lines)
        else:
            formatted_history = "None"

        # 6. Render Prompts (preserves original user query for the final answer)
        system_prompt = self.prompt_loader.render("system", service=target_service)
        query_prompt = self.prompt_loader.render(
            "query_answer",
            service=target_service,
            context_str=context_str,
            chat_history=formatted_history,
            query_str=query_text,
        )

        messages = [Message(role=MessageRole.USER, content=query_prompt)]

        # 7. LLM Generation
        llm_response = await self.llm_provider.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            model=model,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        return QueryResult(
            answer=llm_response.content,
            service=target_service,
            sources=sources,
            provider=llm_response.provider,
            model=llm_response.model,
            latency_ms=round(latency_ms, 2),
            retrieved_chunks_count=len(retrieved_chunks),
        )

    async def stream_query(
        self,
        query_text: str,
        service: Optional[str] = None,
        chat_history: Optional[List[Message]] = None,
        top_k: int = 4,
        temperature: float = 0.1,
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[SourceReference], Dict[str, Any]]:
        """
        Stream RAG response chunks asynchronously with upfront source metadata.
        """
        target_service = service or self.default_service

        # 1. Generate standalone retrieval query for conversation-aware retrieval
        retrieval_query = await self._generate_standalone_query(
            query_text=query_text,
            service=target_service,
            chat_history=chat_history,
        )

        # 2. Embed standalone query and retrieve with service filtering
        query_vector = await self.embedding_provider.embed_query(retrieval_query)
        retrieved_chunks = await self.vector_store.search(
            query_vector=query_vector,
            limit=top_k,
            service_filter=target_service,
        )

        # 3. Assemble context & sources
        context_str, sources = self.context_assembler.assemble(retrieved_chunks)

        # 4. Format Conversation History using configurable limit
        formatted_history = "None"
        if chat_history:
            formatted_history = "\n".join(
                [f"{m.role.value.capitalize()}: {m.content}" for m in chat_history[-self.max_history_messages:]]
            )

        # 5. Render Prompts (preserves original user query for the final answer)
        system_prompt = self.prompt_loader.render("system", service=target_service)
        query_prompt = self.prompt_loader.render(
            "query_answer",
            service=target_service,
            context_str=context_str,
            chat_history=formatted_history,
            query_str=query_text,
        )

        messages = [Message(role=MessageRole.USER, content=query_prompt)]

        # 6. Stream from LLM provider
        stream_iter = self.llm_provider.stream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            model=model,
        )

        provider_name = getattr(self.llm_provider, "provider_name", "groq" if "groq" in getattr(self.llm_provider, "base_url", "") else "openai")
        model_name = model or getattr(self.llm_provider, "model_id", "default")
        meta = {
            "service": target_service,
            "provider": provider_name,
            "model": model_name,
        }

        return stream_iter, sources, meta

