import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
import uuid

from backend_service.app.domain.models.saathi import (
    CustomerRelationship,
    CustomerSummaryDTO,
    RelationshipBrief,
    CustomerFeedback,
    TransitionStatus,
    ActionStatus,
    TransitionActionItem,
    ActionPriority,
    CommitmentItem,
    CommitmentType,
    CommitmentStatus,
    CustomerFact,
    CustomerFactStatus,
    PreCallBriefing,
    ManagementSummary,
    AskSaathiResponse,
    AskEvidenceItem,
    HealthLevel,
    ManualContextItem,
    AddContextRequest,
    CRMInteraction,
)
from backend_service.app.infrastructure.persistence.saathi_seed import get_saathi_seed_data
from backend_service.app.infrastructure.services.saathi_indexer import get_saathi_indexer
from rag_service.domain.models import Message, MessageRole

logger = logging.getLogger(__name__)


class SaathiService:
    """
    Application service managing the complete Saathi Relationship Continuity lifecycle:
    1. 'We Remember': Consolidated CRM interactions, timeline, and AI Relationship Brief.
    2. 'What Do We Owe': Distinguishes confirmed commitments from discussed possibilities.
    3. 'Ask Saathi': Grounded natural-language Q&A with evidence inspection.
    4. 'Customer Validation': Client-confirmed context and memory updates.
    5. 'Pre-Call Briefing': 2-minute actionable preparation.
    6. 'Management Summary': Executive reporting.
    """

    def __init__(self) -> None:
        self._customers: Dict[str, CustomerRelationship] = get_saathi_seed_data()
        self._indexer = get_saathi_indexer()
        self._initial_indexing_done = False

    async def ensure_indexed(self, customer_id: Optional[str] = None) -> None:
        """Ensure customer context is indexed into the dedicated Saathi Qdrant collection."""
        try:
            if customer_id:
                cust = self._customers.get(customer_id)
                if cust:
                    await self._indexer.index_customer(cust)
            else:
                for c in self._customers.values():
                    await self._indexer.index_customer(c)
                self._initial_indexing_done = True
        except Exception as e:
            logger.warning(f"Background Saathi Qdrant indexing note: {e}")

    def list_customers(self) -> List[CustomerSummaryDTO]:
        """List all customer relationship transition cases with health and counts."""
        summaries = []
        for c in self._customers.values():
            pending_actions = sum(1 for a in c.action_items if a.status != ActionStatus.COMPLETED)
            open_commitments = sum(1 for com in c.commitments if com.status != CommitmentStatus.COMPLETED)
            health_level = c.health.level if c.health else HealthLevel.STABLE

            summaries.append(
                CustomerSummaryDTO(
                    id=c.id,
                    name=c.name,
                    tier=c.tier,
                    city=c.city,
                    account_number_masked=c.account_number_masked,
                    aum_display=c.aum_display,
                    tenure_years=c.tenure_years,
                    previous_rm_name=c.previous_rm_name,
                    new_rm_name=c.new_rm_name,
                    status=c.status,
                    transition_date=c.transition_date,
                    avatar_color=c.avatar_color,
                    pending_actions_count=pending_actions,
                    health_level=health_level,
                    open_commitments_count=open_commitments,
                    contradictions_count=len(c.contradictions),
                )
            )
        return summaries

    def get_customer(self, customer_id: str) -> Optional[CustomerRelationship]:
        """Retrieve full relationship profile with all grounding data."""
        customer = self._customers.get(customer_id)
        if customer and not self._initial_indexing_done:
            # Trigger background indexing for quick semantic retrieval
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.ensure_indexed(customer_id))
            except Exception:
                pass
        return customer

    async def add_manual_context(
        self,
        customer_id: str,
        request: AddContextRequest,
    ) -> CustomerRelationship:
        """
        Manually add extra relationship context from the UI for a given customer.
        The context is stored in memory, indexed in the dedicated Qdrant collection,
        and triggers a full AI brief re-synthesis incorporating ALL context.
        """
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        now = datetime.now(timezone.utc)
        note_id = f"ctx-{uuid.uuid4().hex[:8]}"
        created_at_str = now.strftime("%Y-%m-%d %H:%M")

        manual_item = ManualContextItem(
            id=note_id,
            title=request.title,
            category=request.category,
            content=request.content,
            source_channel=request.source_channel,
            recorded_by=request.recorded_by or customer.new_rm_name,
            created_at=created_at_str,
        )

        customer.extra_context.insert(0, manual_item)

        # Also add to interaction history
        customer.interactions.insert(
            0,
            CRMInteraction(
                id=f"int-{note_id}",
                date=now.strftime("%Y-%m-%d"),
                channel=request.source_channel,
                rm_name=manual_item.recorded_by,
                summary=f"[{request.category}] {request.title}: {request.content}",
                tags=["Manual Note", request.category],
            ),
        )

        # 1. Index into dedicated Qdrant collection
        try:
            await self._indexer.index_single_context(customer_id, customer.name, manual_item)
        except Exception as e:
            logger.warning(f"Failed to index manual context in Qdrant: {e}")

        # 2. Re-synthesize AI brief incorporating ALL customer context
        try:
            await self.synthesize_brief(customer_id)
        except Exception as e:
            logger.warning(f"Failed to re-synthesize brief after adding context: {e}")

        return customer

    async def synthesize_brief(self, customer_id: str) -> RelationshipBrief:
        """
        Synthesizes a Relationship Brief for the new RM using CRM touchpoints, commitments,
        facts, and all manually added context retrieved from Qdrant.
        """
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        now_iso = datetime.now(timezone.utc).isoformat()

        # Retrieve comprehensive customer context from Qdrant
        qdrant_context = await self._indexer.get_all_customer_context_text(
            customer_id=customer_id,
            fallback_customer=customer,
        )

        # Dynamic LLM synthesis using resolved providers with automatic fallback
        try:
            manual_notes_section = ""
            if customer.extra_context:
                manual_notes_section = "Latest Manually Recorded Context Notes by RM:\n" + "\n".join(
                    [f"- [{ctx.category}] {ctx.title}: {ctx.content} (by {ctx.recorded_by} via {ctx.source_channel})" for ctx in customer.extra_context]
                ) + "\n\n"

            prompt = (
                f"You are the Saathi Relationship Continuity AI. Synthesize an empathetic, high-level executive brief "
                f"for incoming RM '{customer.new_rm_name}' taking over client '{customer.name}' ({customer.tier.value}, AUM: {customer.aum_display}).\n"
                f"Previous RM: {customer.previous_rm_name} (Transfer Reason: {customer.transfer_reason}).\n\n"
                f"{manual_notes_section}"
                f"All Grounded Customer Context from Qdrant Vector DB:\n{qdrant_context}\n\n"
                f"CRITICAL FORMATTING INSTRUCTIONS:\n"
                f"1. Output a cohesive, polished narrative summary in 2 to 3 paragraphs (around 90 to 160 words).\n"
                f"2. Seamlessly weave together who the client is, relationship tenure/sentiment, core wealth and family priorities, and immediate upcoming commitments/notes.\n"
                f"3. Do NOT use markdown tables or raw pipe (|) table syntax.\n"
                f"4. Do NOT output a document title like '## Executive Summary'. Start directly with the narrative summary.\n"
                f"5. At the very end on a new line, provide 'FIRST_CALL_OPENER: <opener>', a warm 2-sentence conversational opener for the incoming RM acknowledging the previous RM and the primary upcoming topic."
            )

            bp, op, settings = self._resolve_providers()
            llm_text = None
            msg = Message(id=str(uuid.uuid4()), role=MessageRole.USER, content=prompt)

            # 1. Primary: AWS Bedrock
            if bp:
                try:
                    model_id = settings.bedrock_llm_model_id or "anthropic.claude-sonnet-4-6"
                    resp = await bp.generate(messages=[msg], model=model_id, temperature=0.1, max_tokens=1024)
                    if resp and resp.content and resp.content.strip():
                        llm_text = resp.content.strip()
                except Exception as e:
                    logger.warning(f"Bedrock synthesize_brief attempt failed ({e}). Falling back...")

            # 2. Secondary: Groq / OpenAI Fallback
            if not llm_text and op:
                try:
                    fallback_model_id = settings.openai_model_id or "llama-3.3-70b-versatile"
                    resp = await op.generate(messages=[msg], model=fallback_model_id, temperature=0.1, max_tokens=1024)
                    if resp and resp.content and resp.content.strip():
                        llm_text = resp.content.strip()
                except Exception as e:
                    logger.warning(f"Secondary LLM synthesize_brief attempt failed: {e}")

            if llm_text and len(llm_text.strip()) > 40:
                summary_part = llm_text.strip()
                opener_part = None

                # Extract conversation starter if provided
                if "FIRST_CALL_OPENER:" in summary_part:
                    parts = summary_part.split("FIRST_CALL_OPENER:", 1)
                    summary_part = parts[0].strip()
                    opener_part = parts[1].strip()
                elif "First-Call Opener:" in summary_part:
                    parts = summary_part.split("First-Call Opener:", 1)
                    summary_part = parts[0].strip()
                    opener_part = parts[1].strip()

                # Clean up any leading headers like "## Executive Summary"
                import re
                summary_part = re.sub(r"^#{1,4}\s+.*?\n+", "", summary_part).strip()

                # Clean up any raw markdown table rows if model still produced them
                lines = summary_part.splitlines()
                clean_lines = [l for l in lines if not l.strip().startswith("|") and not set(l.strip()) <= {"-", "|", ":"}]
                summary_part = "\n".join(clean_lines).strip()

                if customer.brief and summary_part:
                    customer.brief.executive_summary = summary_part
                    if opener_part and len(opener_part) > 15:
                        clean_opener = opener_part.strip(' \n"\'“”')
                        if "\n### Sources" in clean_opener:
                            clean_opener = clean_opener.split("\n### Sources")[0].strip()
                        elif "\nSources:" in clean_opener:
                            clean_opener = clean_opener.split("\nSources:")[0].strip()
                        customer.brief.conversation_starter = clean_opener
                    customer.brief.synthesized_at = now_iso
                    return customer.brief
        except Exception as e:
            logger.info(f"Using rich pre-seeded/computed brief for Saathi: {e}")

        if customer.brief:
            if customer.extra_context and len(customer.extra_context) > 0:
                latest_note = customer.extra_context[0]
                base_summary = customer.brief.executive_summary.split(" (Latest Note:")[0]
                customer.brief.executive_summary = f"{base_summary} (Latest Note: [{latest_note.category}] {latest_note.title} - {latest_note.content[:120]}...)"
            customer.brief.synthesized_at = now_iso
            return customer.brief

        raise ValueError(f"Brief not available for customer '{customer_id}'.")

    def _resolve_providers(self):
        from rag_service.infrastructure.config import get_settings
        from rag_service.infrastructure.providers.bedrock_llm import BedrockLLMProvider
        from rag_service.infrastructure.providers.openai_llm import OpenAiClientProvider

        settings = get_settings()
        has_aws = bool(
            settings.aws_bearer_token_bedrock
            or (settings.aws_access_key_id and settings.aws_secret_access_key)
        )
        has_openai = bool(settings.groq_api_key or settings.openai_api_key)

        bp = BedrockLLMProvider(settings) if has_aws else None
        op = OpenAiClientProvider(settings) if has_openai else None
        return bp, op, settings

    async def _build_saathi_prompt_and_evidence(
        self, customer: CustomerRelationship, question: str
    ) -> Tuple[str, List[AskEvidenceItem], bool, Optional[str], List[Any], str]:
        """
        Retrieves context from Qdrant, parses evidence, and constructs the anti-hallucination prompt.
        """
        q_lower = question.lower()
        vector_chunks = []
        try:
            vector_chunks = await self._indexer.search_customer_context(
                customer_id=customer.id,
                query=question,
                limit=6,
            )
        except Exception as e:
            logger.warning(f"Saathi Qdrant search note: {e}")

        vector_context_parts = []
        evidence_from_vectors = []
        for c in vector_chunks:
            source = c.metadata.extra.get("source", "Saathi Vector DB")
            date = c.metadata.extra.get("date", "Recorded")
            rm_name = c.metadata.extra.get("rm_name", "RM/Bank")
            com_type = c.metadata.extra.get("commitment_type")
            vector_context_parts.append(
                f"[{c.metadata.extra.get('doc_type', 'Record')} | {source} | Date: {date}]:\n{c.content}"
            )
            evidence_from_vectors.append(
                AskEvidenceItem(
                    date=date,
                    channel=f"Qdrant ({source})",
                    rm_name=rm_name,
                    snippet=c.content[:240],
                    commitment_type=com_type,
                )
            )

        interactions_context = "\n".join(
            [f"Date: {i.date}, Channel: {i.channel}, RM: {i.rm_name}\nNote: {i.summary}" for i in customer.interactions]
        )
        commitments_context = "\n".join(
            [f"Title: {c.title}\nStatus: {c.status.value}\nType: {c.commitment_type.value}\nPromised by: {c.committed_by} on {c.committed_on}\nDetails: {c.details}\nEvidence: {c.evidence_snippet}" for c in customer.commitments]
        )
        facts_context = "\n".join([f"- [{f.category}] {f.statement} (Status: {f.status.value})" for f in customer.facts])
        manual_notes_context = "\n".join([f"- [{m.category}] {m.title}: {m.content} (by {m.recorded_by} on {m.created_at} via {m.source_channel})" for m in customer.extra_context])
        vector_block = "\n\n".join(vector_context_parts) if vector_context_parts else "Use below customer records:"

        llm_prompt = f"""You are Saathi, the Enterprise Relationship Memory & Continuity Assistant.
Answer the following Relationship Manager's question about customer '{customer.name}'.

CRITICAL RULES:
1. Ground your answer ONLY in the provided Customer History, Qdrant Vector Chunks, Commitments, and Manual Notes.
2. If asked about a promise, concession, or discount:
   - Clearly distinguish between a CONFIRMED COMMITMENT (a firm promise or SLA) vs a DISCUSSED POSSIBILITY (an idea or request that was explored but no commitment was made).
3. If the question asks about something that does NOT exist in the record, explicitly state:
   "I couldn't find any record of that in {customer.name}'s history."
4. If the question relates to manual notes or recent context added by the RM, reference it accurately.
5. Format your response cleanly using standard markdown:
   - Use bold for emphasis and key terms.
   - Use bullet points for multiple items or facts.
   - Include a short '### Sources' section at the end citing the specific record or manual note.
6. Be concise, professional, and actionable for a private banker.

RELEVANT VECTOR DB CHUNKS (Collection: saathi_relationship_collection, filtered for customer_id='{customer.id}'):
{vector_block}

MANUAL RELATIONSHIP CONTEXT NOTES:
{manual_notes_context or 'None recorded yet.'}

CUSTOMER FACTS:
{facts_context}

OUTSTANDING COMMITMENTS & PROMISES:
{commitments_context}

HISTORICAL INTERACTIONS:
{interactions_context}

QUESTION: {question}

Provide your answer concisely using properly structured markdown."""

        # Evidence detection
        evidence_list = evidence_from_vectors[:3]
        if not evidence_list:
            for int_item in customer.interactions:
                if any(word in int_item.summary.lower() for word in q_lower.split() if len(word) > 4):
                    evidence_list.append(
                        AskEvidenceItem(
                            date=int_item.date,
                            channel=int_item.channel,
                            rm_name=int_item.rm_name,
                            snippet=int_item.summary,
                        )
                    )

        is_com = any(k in q_lower for k in ["promise", "concession", "owe", "discount", "preferential", "tuition", "rate", "commitment"])
        com_type = "confirmed_commitment" if ("home loan" in q_lower or "25 bps" in q_lower) else ("discussed_possibility" if ("tuition" in q_lower or "forex" in q_lower) else None)
        drilldown = f"Grounded via Qdrant Vector DB ({len(vector_chunks)} chunks) across {len(customer.interactions)} CRM records and {len(customer.extra_context)} manual context notes."

        return llm_prompt, evidence_list, is_com, com_type, vector_chunks, drilldown

    async def ask_saathi_stream(self, customer_id: str, question: str) -> AsyncIterator[str]:
        """
        Streams natural-language Ask Saathi response using AWS Bedrock Sonnet 4.6 by default,
        with transparent fallback to secondary LLMs (Groq / OpenAI) or offline reasoning.
        Emits SSE events: metadata, chunks, and done.
        """
        customer = self._customers.get(customer_id)
        if not customer:
            yield f"data: {json.dumps({'type': 'error', 'error': f'Customer {customer_id} not found.'})}\n\n"
            return

        prompt, evidence_list, is_com, com_type, vector_chunks, drilldown = (
            await self._build_saathi_prompt_and_evidence(customer, question)
        )

        bp, op, settings = self._resolve_providers()
        chosen_model = "Claude Sonnet 4.6 (AWS Bedrock)"
        is_fallback = False
        stream_source = None

        # 1. Primary: AWS Bedrock Sonnet 4.6
        if bp:
            try:
                msg = Message(id=str(uuid.uuid4()), role=MessageRole.USER, content=prompt)
                stream_iter = bp.stream(
                    messages=[msg],
                    model="anthropic.claude-sonnet-4-6",
                    temperature=0.1,
                    max_tokens=2048,
                )
                first_chunk = await anext(stream_iter, None)
                if first_chunk is not None:
                    chosen_model = "Claude Sonnet 4.6 (AWS Bedrock)"
                    is_fallback = False

                    async def _bedrock_stream():
                        yield first_chunk
                        async for c in stream_iter:
                            yield c

                    stream_source = _bedrock_stream()
            except Exception as e:
                logger.warning(f"Bedrock Sonnet 4.6 unavailable or failed ({e}). Falling back to secondary LLM...")

        # 2. Fallback: Groq / OpenAI LLM
        if stream_source is None and op:
            try:
                msg = Message(id=str(uuid.uuid4()), role=MessageRole.USER, content=prompt)
                fallback_model_id = settings.openai_model_id or "llama-3.3-70b-versatile"
                fallback_display = (
                    "Llama 3.3 70B (Groq Fallback)"
                    if "llama" in fallback_model_id.lower()
                    else f"{fallback_model_id} (Fallback)"
                )
                stream_iter = op.stream(
                    messages=[msg],
                    model=fallback_model_id,
                    temperature=0.1,
                    max_tokens=2048,
                )
                first_chunk = await anext(stream_iter, None)
                if first_chunk is not None:
                    chosen_model = fallback_display
                    is_fallback = True

                    async def _openai_stream():
                        yield first_chunk
                        async for c in stream_iter:
                            yield c

                    stream_source = _openai_stream()
            except Exception as e:
                logger.warning(f"Secondary LLM fallback failed ({e}). Falling back to deterministic engine...")

        # 3. Fallback: Offline Deterministic Reasoning
        if stream_source is None:
            is_fallback = True
            chosen_model = "Saathi Grounded Engine (Offline Fallback)"
            # Check manual notes first
            q_lower = question.lower()
            matched_note = None
            for note in customer.extra_context:
                if any(w in note.content.lower() or w in note.title.lower() for w in q_lower.split() if len(w) > 3):
                    matched_note = note
                    break

            if matched_note:
                fallback_text = (
                    f"**Yes.** According to the manual context note **{matched_note.title}** recorded by {matched_note.recorded_by} ({matched_note.category}):\n\n"
                    f"{matched_note.content}\n\n"
                    f"### Sources\n- Manual RM Note ({matched_note.source_channel}, {matched_note.created_at}) — \"{matched_note.title}\""
                )
            else:
                det_resp = self._deterministic_ask(customer, question, q_lower)
                fallback_text = det_resp.answer

            async def _offline_stream():
                words = fallback_text.split(" ")
                for i, w in enumerate(words):
                    yield w + (" " if i < len(words) - 1 else "")
                    await asyncio.sleep(0.012)

            stream_source = _offline_stream()

        # Emit initial metadata
        meta_payload = {
            "type": "metadata",
            "model": chosen_model,
            "is_fallback": is_fallback,
            "evidence": [ev.model_dump() for ev in evidence_list],
            "is_commitment": is_com,
            "commitment_type": com_type,
            "drilldown_context": drilldown,
        }
        yield f"data: {json.dumps(meta_payload)}\n\n"

        # Emit token chunks
        full_chunks = []
        async for chunk in stream_source:
            if chunk:
                full_chunks.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

        # Emit completion
        full_answer = "".join(full_chunks)
        done_payload = {
            "type": "done",
            "answer": full_answer,
            "model": chosen_model,
            "is_fallback": is_fallback,
            "confidence": "high",
            "drilldown_context": drilldown,
        }
        yield f"data: {json.dumps(done_payload)}\n\n"

    async def ask_saathi(self, customer_id: str, question: str) -> AskSaathiResponse:
        """
        Non-streaming Ask Saathi with AWS Bedrock Sonnet 4.6 default and transparent fallback.
        """
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        prompt, evidence_list, is_com, com_type, vector_chunks, drilldown = (
            await self._build_saathi_prompt_and_evidence(customer, question)
        )

        bp, op, settings = self._resolve_providers()
        chosen_model = "Claude Sonnet 4.6 (AWS Bedrock)"
        is_fallback = False

        # 1. Try Bedrock Sonnet 4.6
        if bp:
            try:
                msg = Message(id=str(uuid.uuid4()), role=MessageRole.USER, content=prompt)
                resp = await bp.generate(
                    messages=[msg],
                    model="anthropic.claude-sonnet-4-6",
                    temperature=0.1,
                    max_tokens=2048,
                )
                if resp.content and len(resp.content) > 20:
                    return AskSaathiResponse(
                        question=question,
                        answer=resp.content,
                        is_commitment=is_com,
                        commitment_type=com_type or ("confirmed_commitment" if "confirmed" in resp.content.lower() else ("discussed_possibility" if "discussed" in resp.content.lower() else "none")),
                        evidence=evidence_list,
                        confidence="high",
                        drilldown_context=drilldown,
                        model="Claude Sonnet 4.6 (AWS Bedrock)",
                        is_fallback=False,
                    )
            except Exception as e:
                logger.warning(f"Bedrock Sonnet 4.6 generation failed ({e}). Falling back to secondary LLM...")

        # 2. Try Groq / OpenAI
        if op:
            try:
                msg = Message(id=str(uuid.uuid4()), role=MessageRole.USER, content=prompt)
                fallback_model_id = settings.openai_model_id or "llama-3.3-70b-versatile"
                fallback_display = (
                    "Llama 3.3 70B (Groq Fallback)"
                    if "llama" in fallback_model_id.lower()
                    else f"{fallback_model_id} (Fallback)"
                )
                resp = await op.generate(
                    messages=[msg],
                    model=fallback_model_id,
                    temperature=0.1,
                    max_tokens=2048,
                )
                if resp.content and len(resp.content) > 20:
                    return AskSaathiResponse(
                        question=question,
                        answer=resp.content,
                        is_commitment=is_com,
                        commitment_type=com_type or ("confirmed_commitment" if "confirmed" in resp.content.lower() else ("discussed_possibility" if "discussed" in resp.content.lower() else "none")),
                        evidence=evidence_list,
                        confidence="high",
                        drilldown_context=drilldown,
                        model=fallback_display,
                        is_fallback=True,
                    )
            except Exception as e:
                logger.warning(f"Secondary LLM generation failed ({e}). Falling back to deterministic engine...")

        # 3. Deterministic Fallback
        det_resp = self._deterministic_ask(customer, question, question.lower())
        det_resp.model = "Saathi Grounded Engine (Offline Fallback)"
        det_resp.is_fallback = True
        return det_resp

    def _deterministic_ask(self, customer: CustomerRelationship, question: str, q_lower: str) -> AskSaathiResponse:
        """Deterministic fallback grounding RM questions against customer history."""
        evidence_list: List[AskEvidenceItem] = []

        # Case 1: Concessions / Overseas tuition / Education pricing
        if any(k in q_lower for k in ["concession", "tuition", "overseas education", "education pricing"]):
            if customer.id == "cust-nri-rahul-sharma":
                evidence_list.append(
                    AskEvidenceItem(
                        date="2026-08-18",
                        channel="Phone Call",
                        rm_name="Kunal Deshmukh",
                        snippet="Customer enquired whether any preferential forex margin is possible on tuition; Kunal clarified bank will review margins once tuition invoice is submitted, but no concession was promised.",
                        commitment_type="discussed_possibility",
                    )
                )
                return AskSaathiResponse(
                    question=question,
                    answer="No confirmed concession was promised for overseas tuition. During the 18 Aug phone call, Rahul enquired about preferential forex margins for daughter Ananya's UCL London fees; Kunal Deshmukh noted the bank could review margins upon receiving the invoice, but explicitly did not record or promise a concession. (Note: A 25 bps spread discount WAS confirmed on his Gurgaon home loan).",
                    is_commitment=True,
                    commitment_type="discussed_possibility",
                    evidence=evidence_list,
                    confidence="high",
                    drilldown_context="Interaction #int-101 (2026-08-18 Phone Call)",
                )

        # Case 2: What was customer discussing with previous RM?
        if any(k in q_lower for k in ["previous rm", "discussing", "last interaction", "what was discussed"]):
            last_int = customer.interactions[0] if customer.interactions else None
            if last_int:
                evidence_list.append(
                    AskEvidenceItem(
                        date=last_int.date,
                        channel=last_int.channel,
                        rm_name=last_int.rm_name,
                        snippet=last_int.summary,
                    )
                )
                return AskSaathiResponse(
                    question=question,
                    answer=f"In the most recent interaction on {last_int.date} with {last_int.rm_name} via {last_int.channel}, the discussion focused on: {last_int.summary}",
                    is_commitment=False,
                    commitment_type="none",
                    evidence=evidence_list,
                    confidence="high",
                    drilldown_context=f"Recorded by {last_int.rm_name} on {last_int.date}",
                )

        # Case 3: Priorities & What matters
        if any(k in q_lower for k in ["priority", "priorities", "what matters", "focus"]):
            priorities = customer.brief.customer_priorities if customer.brief else [f.statement for f in customer.facts[:3]]
            return AskSaathiResponse(
                question=question,
                answer=f"The primary recorded priorities for {customer.name} are:\n" + "\n".join([f"• {p}" for p in priorities]),
                is_commitment=False,
                commitment_type="none",
                evidence=[
                    AskEvidenceItem(
                        date=customer.transition_date,
                        channel="Relationship Brief",
                        rm_name=customer.previous_rm_name,
                        snippet="; ".join(priorities),
                    )
                ],
                confidence="high",
            )

        # Case 4: Communication preferences / when to call
        if any(k in q_lower for k in ["contact", "preference", "call", "timing", "when to"]):
            prefs = customer.brief.explicit_preferences if customer.brief else ["Check latest interaction note."]
            return AskSaathiResponse(
                question=question,
                answer=f"Explicit communication preferences for {customer.name}:\n" + "\n".join([f"• {p}" for p in prefs]),
                is_commitment=False,
                commitment_type="none",
                evidence=[
                    AskEvidenceItem(
                        date=customer.interactions[-1].date if customer.interactions else customer.transition_date,
                        channel="Client Preference Record",
                        rm_name=customer.previous_rm_name,
                        snippet="; ".join(prefs),
                    )
                ],
                confidence="high",
            )

        # Case 5: What do we owe / what to follow up on
        if any(k in q_lower for k in ["owe", "follow up", "pending", "action", "unresolved"]):
            comms = [f"• [{c.commitment_type.value.upper()}] {c.title} ({c.status.value}): {c.details}" for c in customer.commitments]
            return AskSaathiResponse(
                question=question,
                answer=f"Outstanding commitments and follow-ups for {customer.name}:\n" + "\n".join(comms),
                is_commitment=True,
                commitment_type="confirmed_commitment",
                evidence=[
                    AskEvidenceItem(
                        date=c.committed_on,
                        channel="Commitment Tracker",
                        rm_name=c.committed_by,
                        snippet=c.details,
                        commitment_type=c.commitment_type.value,
                    )
                    for c in customer.commitments
                ],
                confidence="high",
            )

        # Generic grounded fallback
        return AskSaathiResponse(
            question=question,
            answer=f"Based on {customer.name}'s verified relationship record ({customer.tenure_years} years tenure, {customer.tier.value}), the bank has recorded: {customer.brief.executive_summary if customer.brief else 'Relationship active under Saathi management.'}",
            is_commitment=False,
            commitment_type="none",
            evidence=[
                AskEvidenceItem(
                    date=customer.transition_date,
                    channel="Relationship Synthesis",
                    rm_name=customer.previous_rm_name,
                    snippet=customer.brief.client_sentiment if customer.brief else "Active relationship.",
                )
            ],
            confidence="medium",
        )

    def validate_customer_fact(
        self,
        customer_id: str,
        fact_id: str,
        action: str,
        updated_text: Optional[str] = None,
    ) -> CustomerRelationship:
        """
        Step 4 in Saathi Journey ('Customer Validation'):
        Allows customer or RM to mark a fact as 'confirmed', 'updated', or 'no_longer_relevant'.
        Evolves relationship memory in real time.
        """
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        now_iso = datetime.now(timezone.utc).isoformat()[:10]

        for fact in customer.facts:
            if fact.id == fact_id:
                if action == "confirm":
                    fact.status = CustomerFactStatus.CONFIRMED
                    fact.last_updated = now_iso
                elif action == "update":
                    fact.status = CustomerFactStatus.UPDATED
                    fact.updated_note = updated_text
                    fact.last_updated = now_iso
                elif action == "mark_irrelevant":
                    fact.status = CustomerFactStatus.NO_LONGER_RELEVANT
                    fact.last_updated = now_iso
                    # Remove from active priorities in the brief if present
                    if customer.brief:
                        customer.brief.customer_priorities = [
                            p for p in customer.brief.customer_priorities if fact.statement[:25].lower() not in p.lower()
                        ]
                return customer

        raise ValueError(f"Fact '{fact_id}' not found for customer '{customer_id}'.")

    def update_commitment_status(
        self,
        customer_id: str,
        commitment_id: str,
        new_status: CommitmentStatus,
    ) -> CommitmentItem:
        """Update status of a tracked relationship commitment."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        for c in customer.commitments:
            if c.id == commitment_id:
                c.status = new_status
                return c

        raise ValueError(f"Commitment '{commitment_id}' not found for customer '{customer_id}'.")

    def get_pre_call_brief(self, customer_id: str) -> Optional[PreCallBriefing]:
        """Retrieve 2-minute pre-call briefing."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")
        return customer.pre_call_brief

    def get_management_summary(self, customer_id: str) -> Optional[ManagementSummary]:
        """Retrieve executive management summary."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")
        return customer.management_summary

    def submit_customer_feedback(
        self,
        customer_id: str,
        customer_notes: str,
        corrected_items: Optional[List[str]] = None,
    ) -> CustomerRelationship:
        """Records client's additions, notes, or verification."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        now_iso = datetime.now(timezone.utc).isoformat()
        items = corrected_items or []
        if not items and customer_notes:
            items = [f"Client added custom note: '{customer_notes[:60]}...'"]

        customer.feedback = CustomerFeedback(
            confirmed_at=now_iso,
            customer_notes=customer_notes,
            corrected_items=items,
            has_verified=True,
        )
        customer.status = TransitionStatus.CUSTOMER_CONFIRMED

        # Add a new transition action item reflecting the customer's input
        if customer_notes:
            new_action = TransitionActionItem(
                id=f"act-cust-{len(customer.action_items) + 1}",
                title=f"Client Verified Request: {customer_notes[:45]}...",
                description=customer_notes,
                category="Customer Additions",
                priority=ActionPriority.HIGH,
                status=ActionStatus.PENDING,
                sla_date=now_iso[:10],
                assigned_to=customer.new_rm_name,
            )
            customer.action_items.insert(0, new_action)

        return customer

    def update_action_status(
        self,
        customer_id: str,
        action_id: str,
        new_status: ActionStatus,
    ) -> TransitionActionItem:
        """Update status of an action item in the handover tracker."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        for item in customer.action_items:
            if item.id == action_id:
                item.status = new_status
                if all(a.status == ActionStatus.COMPLETED for a in customer.action_items):
                    customer.status = TransitionStatus.COMPLETED
                return item

        raise ValueError(f"Action item '{action_id}' not found for customer '{customer_id}'.")

    def complete_handover(
        self,
        customer_id: str,
        new_rm_notes: Optional[str] = None,
    ) -> CustomerRelationship:
        """New RM formally acknowledges handover and marks it active."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        customer.status = TransitionStatus.HANDOVER_ACTIVE
        return customer

    def reset_demo(self) -> None:
        """Reset all demo scenarios to initial states."""
        self._customers = get_saathi_seed_data()


_saathi_service: Optional[SaathiService] = None


def get_saathi_service() -> SaathiService:
    global _saathi_service
    if _saathi_service is None:
        _saathi_service = SaathiService()
    return _saathi_service
