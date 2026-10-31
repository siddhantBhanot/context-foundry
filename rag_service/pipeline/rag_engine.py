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
from rag_service.ingestion.repo_map import RepoMapBuilder
from rag_service.ingestion.symbol_graph import EdgeType, NodeType, SymbolGraphIndex
from rag_service.prompts.loader import PromptLoader, get_prompt_loader

logger = logging.getLogger("rag_service.pipeline")

MAX_HISTORY_MESSAGES: int = 6


class ContextAssembler:
    """
    Assembles retrieved chunks (plus the microservice RepoMap blueprint and 1-hop
    collaborators) into structured context text and extracts verified source citations.
    """

    @staticmethod
    def assemble(
        chunks: List[Chunk],
        service: Optional[str] = None,
        query_text: Optional[str] = None,
        max_context_chars: int = 9200,
    ) -> Tuple[str, List[SourceReference]]:
        focus_files = [c.metadata.file_path for c in chunks if c.metadata.file_path]
        repo_map_budget = 8000 if max_context_chars >= 20000 else 2600
        chunk_char_cap = 4500 if max_context_chars >= 20000 else 1800
        repo_map_md = (
            RepoMapBuilder.load_markdown(
                service,
                focus_files=focus_files,
                query_text=query_text,
                max_chars=repo_map_budget,
            )
            if service
            else None
        )

        if not chunks and not repo_map_md:
            return "No matching documentation or source code found for the query.", []

        context_blocks: List[str] = []
        used_chars = 0
        if repo_map_md:
            bp_block = f"[Repository Architecture Blueprint]\n{repo_map_md}\n"
            context_blocks.append(bp_block)
            used_chars += len(bp_block)

        if service:
            # Extract seed methods from retrieved chunks to build grounded Call Hierarchy Trace
            seed_methods: List[str] = []
            for c in chunks:
                if c.metadata.method_name and c.metadata.method_name not in seed_methods:
                    seed_methods.append(c.metadata.method_name)
                for m in (c.metadata.extra or {}).get("methods_in_file", []):
                    if m and m not in seed_methods:
                        seed_methods.append(m)

            if seed_methods:
                try:
                    graph_idx = SymbolGraphIndex.load(service)
                    if graph_idx:
                        trace_lines = graph_idx.build_call_hierarchy_trace(seed_methods[:4])
                        if trace_lines:
                            trace_block = "[Architecture Call Hierarchy Trace]\n" + "\n".join(trace_lines) + "\n"
                            context_blocks.append(trace_block)
                            used_chars += len(trace_block)
                except Exception as e:
                    logger.debug("Failed to build call hierarchy trace: %s", e)

        sources: List[SourceReference] = []
        seen_files = set()

        for idx, chunk in enumerate(chunks, start=1):
            meta = chunk.metadata
            file_ref = meta.file_path

            header_info = f"[Source {idx}: {file_ref}"
            if meta.language:
                header_info += f" | Lang: {meta.language}"
            if meta.class_name:
                header_info += f" | Class: {meta.class_name}"
            if meta.method_name:
                header_info += f" | Method: {meta.method_name}"
            if meta.endpoint:
                header_info += f" | Endpoint: {meta.endpoint}"
            if meta.start_line and meta.end_line:
                header_info += f" | Lines: {meta.start_line}-{meta.end_line}"
            header_info += "]"

            chunk_body = chunk.content
            if len(chunk_body) > chunk_char_cap:
                chunk_body = chunk_body[:chunk_char_cap] + "\n// ... [truncated for token budget]"

            block_str = f"{header_info}\n{chunk_body}\n"
            if used_chars + len(block_str) > max_context_chars and len(context_blocks) > 2:
                break

            context_blocks.append(block_str)
            used_chars += len(block_str)

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

        return "\n---------------------\n".join(context_blocks), sources


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.
    Orchestrates conversational query rewriting, Hybrid Search (Dense Jina-Code-v2 +
    Sparse BM25 RRF), 1-Hop Dependency Expansion, RepoMap blueprint injection,
    and grounded LLM generation.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        prompt_loader: Optional[PromptLoader] = None,
        default_service: str = "default-service",
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
        model: Optional[str] = None,
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
                max_tokens=512,
                model=model,
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

    async def _retrieve_with_expansion(
        self,
        retrieval_query: str,
        target_service: str,
        top_k: int,
    ) -> List[Chunk]:
        """
        Execute Hybrid Search (Dense + BM25 RRF) followed by 1-Hop Dependency Expansion
        using collaborator symbols extracted during structural chunking.
        """
        query_vector = await self.embedding_provider.embed_query(retrieval_query)

        try:
            retrieved_chunks = await self.vector_store.search(
                query_vector=query_vector,
                limit=top_k,
                service_filter=target_service,
                query_text=retrieval_query,
            )
        except TypeError:
            # Backward compatibility for custom/mock vector stores without query_text param
            retrieved_chunks = await self.vector_store.search(
                query_vector=query_vector,
                limit=top_k,
                service_filter=target_service,
            )

        if not retrieved_chunks or not hasattr(self.vector_store, "fetch_by_symbols"):
            return retrieved_chunks

        # Collect 1-hop symbols:
        # (A) Outgoing collaborators referenced by primary retrieved chunks
        # (B) Incoming callers / endpoint controllers from RepoMap that depend on retrieved classes or match query stems
        existing_ids = {c.id for c in retrieved_chunks}
        existing_classes = {c.metadata.class_name for c in retrieved_chunks if c.metadata.class_name}
        candidate_symbols: List[str] = []

        import re
        q_lower = retrieval_query.lower()
        q_stems = {w[:5] for w in re.findall(r"[a-zA-Z]{4,}", q_lower)}
        wants_endpoints = any(
            k in q_lower for k in ("endpoint", "api", "route", "controller", "rest", "graphql", "paginat", "page")
        )

        # 1. Check RepoMap for incoming callers (e.g. Controllers calling retrieved Services/Page models)
        repo_map = RepoMapBuilder.load(target_service)
        if repo_map and repo_map.get("files"):
            files_map = repo_map["files"]
            # Find symbols matching query stems (e.g. "paginat" -> "Page", "CursorPager")
            stem_matched_classes = set()
            for f_info in files_map.values():
                for cls_name in f_info.get("classes") or []:
                    if any(stem in cls_name.lower() for stem in q_stems if len(stem) >= 4):
                        stem_matched_classes.add(cls_name)
                if "paginat" in q_lower or "page" in q_lower or "cursor" in q_lower:
                    for cls_name in f_info.get("classes") or []:
                        if any(p in cls_name.lower() for p in ("page", "cursor")):
                            stem_matched_classes.add(cls_name)

            target_deps = existing_classes | stem_matched_classes
            caller_candidates: List[Tuple[int, str]] = []
            for f_info in files_map.values():
                f_deps = set(f_info.get("dependencies") or [])
                f_classes = f_info.get("classes") or []
                if not f_classes:
                    continue
                overlap = len(f_deps & target_deps)
                has_ep = 1 if (f_info.get("endpoints") or any("api" in c.lower() or "datafetcher" in c.lower() or "controller" in c.lower() for c in f_classes)) else 0
                if overlap > 0:
                    score = overlap * 2 + (3 if (wants_endpoints and has_ep) else has_ep)
                    for cls_name in f_classes:
                        if cls_name not in existing_classes:
                            caller_candidates.append((score, cls_name))

            caller_candidates.sort(key=lambda x: x[0], reverse=True)
            for _, cls_name in caller_candidates[:4]:
                if cls_name not in candidate_symbols:
                    candidate_symbols.append(cls_name)

            for cls_name in stem_matched_classes:
                if cls_name not in existing_classes and cls_name not in candidate_symbols:
                    candidate_symbols.append(cls_name)

        # 2. Outgoing dependencies from retrieved chunks
        for c in retrieved_chunks:
            deps = (c.metadata.extra or {}).get("dependencies", [])
            for dep in deps:
                if dep and dep not in existing_classes and dep not in candidate_symbols:
                    candidate_symbols.append(dep)

        if candidate_symbols:
            try:
                expanded_chunks = await self.vector_store.fetch_by_symbols(
                    service=target_service,
                    symbols=candidate_symbols[:10],
                    limit=4,
                )
                for ec in expanded_chunks:
                    if ec.id not in existing_ids:
                        retrieved_chunks.append(ec)
                        existing_ids.add(ec.id)
            except Exception as e:
                logger.debug("1-hop dependency expansion skipped: %s", e)

        # 3. Method-Level Multi-Hop Graph Traversal (Callees, Callers, Implementations)
        try:
            if hasattr(self.vector_store, "fetch_by_methods"):
                graph_idx = SymbolGraphIndex.load(target_service)
                if graph_idx:
                    seed_methods: List[str] = []
                    for c in retrieved_chunks:
                        if c.metadata.method_name and c.metadata.method_name not in seed_methods:
                            seed_methods.append(c.metadata.method_name)
                        for m in (c.metadata.extra or {}).get("methods_in_file", []):
                            if m and m not in seed_methods:
                                seed_methods.append(m)

                    target_methods: List[str] = []
                    for sm in seed_methods[:4]:
                        # Outgoing calls (callees up to 2 hops)
                        for node, depth, edge_type in graph_idx.traverse(
                            sm,
                            direction="outgoing",
                            max_depth=2,
                            edge_types={EdgeType.CALLS, EdgeType.IMPLEMENTS},
                        ):
                            if node.node_type == NodeType.METHOD and node.name not in target_methods:
                                target_methods.append(node.name)

                        # Incoming callers / endpoints (1 hop)
                        for node, depth, edge_type in graph_idx.traverse(
                            sm,
                            direction="incoming",
                            max_depth=1,
                            edge_types={EdgeType.CALLED_BY, EdgeType.INVOKES},
                        ):
                            if node.node_type == NodeType.METHOD and node.name not in target_methods:
                                target_methods.append(node.name)

                    if target_methods:
                        method_chunks = await self.vector_store.fetch_by_methods(
                            service=target_service,
                            methods=target_methods[:8],
                            limit=3,
                        )
                        for mc in method_chunks:
                            if mc.id not in existing_ids:
                                retrieved_chunks.append(mc)
                                existing_ids.add(mc.id)
        except Exception as e:
            logger.debug("Method-level graph expansion skipped: %s", e)

        return retrieved_chunks

    def _resolve_budgets(self, model: Optional[str]) -> Tuple[int, int]:
        """Return (max_context_chars, max_output_tokens) based on target provider."""
        provider_name = ""
        if hasattr(self.llm_provider, "resolve_meta"):
            provider_name, _ = self.llm_provider.resolve_meta(model)
        else:
            provider_name = getattr(self.llm_provider, "provider_name", "")
        m_lower = (model or "").lower()
        if provider_name == "gemini" or "gemini" in m_lower or "gemma" in m_lower:
            return 28000, 8192
        return 9200, 3072

    async def query(
        self,
        query_text: str,
        service: Optional[str] = None,
        chat_history: Optional[List[Message]] = None,
        top_k: int = 5,
        temperature: float = 0.1,
        model: Optional[str] = None,
    ) -> QueryResult:
        """
        Execute full RAG query workflow with Hybrid Search, 1-Hop Expansion, and RepoMap injection.
        """
        start_time = time.perf_counter()
        target_service = service or self.default_service
        max_ctx_chars, max_out_tokens = self._resolve_budgets(model)

        # 1. Generate standalone retrieval query for conversation-aware retrieval
        retrieval_query = await self._generate_standalone_query(
            query_text=query_text,
            service=target_service,
            chat_history=chat_history,
            model=model,
        )

        # 2. Hybrid retrieve + 1-hop collaborator expansion
        retrieved_chunks = await self._retrieve_with_expansion(
            retrieval_query=retrieval_query,
            target_service=target_service,
            top_k=top_k,
        )

        # 3. Assemble Context (with RepoMap blueprint) & Citations
        context_str, sources = self.context_assembler.assemble(
            retrieved_chunks,
            service=target_service,
            query_text=retrieval_query,
            max_context_chars=max_ctx_chars,
        )

        # 4. Format Conversation History using configurable limit
        formatted_history = "None"
        if chat_history:
            history_lines = [
                f"{m.role.value.capitalize()}: {m.content[:400]}"
                for m in chat_history[-self.max_history_messages:]
            ]
            formatted_history = "\n".join(history_lines)

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

        # 6. LLM Generation
        llm_response = await self.llm_provider.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_out_tokens,
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
        top_k: int = 5,
        temperature: float = 0.1,
        model: Optional[str] = None,
    ) -> Tuple[AsyncIterator[str], List[SourceReference], Dict[str, Any]]:
        """
        Stream RAG response chunks asynchronously with upfront source metadata.
        """
        target_service = service or self.default_service
        max_ctx_chars, max_out_tokens = self._resolve_budgets(model)

        # 1. Generate standalone retrieval query for conversation-aware retrieval
        retrieval_query = await self._generate_standalone_query(
            query_text=query_text,
            service=target_service,
            chat_history=chat_history,
            model=model,
        )

        # 2. Hybrid retrieve + 1-hop collaborator expansion
        retrieved_chunks = await self._retrieve_with_expansion(
            retrieval_query=retrieval_query,
            target_service=target_service,
            top_k=top_k,
        )

        # 3. Assemble context (with RepoMap blueprint) & sources
        context_str, sources = self.context_assembler.assemble(
            retrieved_chunks,
            service=target_service,
            query_text=retrieval_query,
            max_context_chars=max_ctx_chars,
        )

        # 4. Format Conversation History using configurable limit
        formatted_history = "None"
        if chat_history:
            formatted_history = "\n".join(
                [f"{m.role.value.capitalize()}: {m.content[:400]}" for m in chat_history[-self.max_history_messages:]]
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
            max_tokens=max_out_tokens,
            model=model,
        )

        if hasattr(self.llm_provider, "resolve_meta"):
            provider_name, model_name = self.llm_provider.resolve_meta(model)
        else:
            provider_name = getattr(
                self.llm_provider,
                "provider_name",
                "groq" if "groq" in getattr(self.llm_provider, "base_url", "") else "openai",
            )
            model_name = model or getattr(self.llm_provider, "model_id", "default")
        meta = {
            "service": target_service,
            "provider": provider_name,
            "model": model_name,
        }

        return stream_iter, sources, meta
