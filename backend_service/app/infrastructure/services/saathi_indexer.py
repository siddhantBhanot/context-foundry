import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional

from backend_service.app.domain.models.saathi import (
    CustomerRelationship,
    ManualContextItem,
)
from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata
from rag_service.domain.protocols import EmbeddingProvider, VectorStore
from rag_service.infrastructure.config import Settings, get_settings

logger = logging.getLogger("saathi.indexer")


class SaathiIndexer:
    """
    Dedicated indexer for the Saathi Relationship Continuity Portal.
    Manages semantic indexing and retrieval inside the isolated Qdrant
    collection (`saathi_relationship_collection`).
    Ensures strict customer-level isolation with `customer_id` metadata filtering.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._init_providers(vector_store, embedding_provider)
        self._indexed_customer_hashes: Dict[str, str] = {}

    def _init_providers(
        self,
        vector_store: Optional[VectorStore],
        embedding_provider: Optional[EmbeddingProvider],
    ) -> None:
        try:
            if embedding_provider is not None:
                self.embedding_provider = embedding_provider
            else:
                from rag_service.infrastructure.providers.bedrock_embedding import (
                    BedrockEmbeddingProvider,
                )
                from rag_service.infrastructure.providers.qdrant_embedding import (
                    QdrantEmbeddingProvider,
                )

                has_aws = bool(
                    self.settings.aws_bearer_token_bedrock
                    or (
                        self.settings.aws_access_key_id
                        and self.settings.aws_secret_access_key
                    )
                )
                if self.settings.embedding_provider == "bedrock" and has_aws:
                    self.embedding_provider = BedrockEmbeddingProvider(self.settings)
                else:
                    self.embedding_provider = QdrantEmbeddingProvider(self.settings)

            if vector_store is not None:
                self.vector_store = vector_store
            else:
                from rag_service.infrastructure.providers.qdrant_store import (
                    QdrantVectorStoreAdapter,
                )

                self.settings.embedding_dimension = self.embedding_provider.dimension
                self.vector_store = QdrantVectorStoreAdapter(
                    settings=self.settings,
                    collection_name=self.settings.qdrant_saathi_collection_name,
                )
        except Exception as e:
            logger.error(f"Failed to initialize Saathi vector store/embedding: {e}")
            from rag_service.run_local import LocalSimulatedVectorStore
            from rag_service.infrastructure.providers.qdrant_embedding import QdrantEmbeddingProvider

            self.embedding_provider = QdrantEmbeddingProvider(self.settings)
            self.vector_store = LocalSimulatedVectorStore()

    def _build_customer_chunks(self, customer: CustomerRelationship) -> List[Chunk]:
        """Convert all dimensions of a customer relationship into semantic chunks with metadata."""
        chunks: List[Chunk] = []

        # 1. Customer Profile Chunk
        profile_text = (
            f"Customer Profile Overview: {customer.name}\n"
            f"Tier: {customer.tier.value} ({customer.segment_description})\n"
            f"City: {customer.city} | Account: {customer.account_number_masked}\n"
            f"AUM: {customer.aum_display} | Tenure: {customer.tenure_years} years with the Bank\n"
            f"Relationship Transition: Former RM {customer.previous_rm_name} ({customer.previous_rm_role}) "
            f"handed over to {customer.new_rm_name} ({customer.new_rm_role}) due to: {customer.transfer_reason}.\n"
            f"Transition Date: {customer.transition_date}."
        )
        chunks.append(
            Chunk(
                id=f"{customer.id}_profile",
                content=profile_text,
                metadata=ServiceMetadata(
                    service="saathi",
                    document_type=DocumentType.OTHER,
                    source="customer_profile",
                    file_path=f"saathi/{customer.id}/profile.txt",
                    extra={
                        "customer_id": customer.id,
                        "customer_name": customer.name,
                        "doc_type": "customer_profile",
                        "category": "Profile",
                        "source": "Core Profile",
                    },
                ),
            )
        )

        # 2. CRM Interactions
        for idx, inter in enumerate(customer.interactions):
            inter_text = (
                f"CRM Interaction Log on {inter.date} via {inter.channel} (Recorded by RM {inter.rm_name}):\n"
                f"Summary: {inter.summary}\n"
                f"Tags: {', '.join(inter.tags)}"
            )
            chunks.append(
                Chunk(
                    id=f"{customer.id}_int_{inter.id}",
                    content=inter_text,
                    metadata=ServiceMetadata(
                        service="saathi",
                        document_type=DocumentType.OTHER,
                        source=inter.channel,
                        file_path=f"saathi/{customer.id}/interactions/{inter.id}.txt",
                        extra={
                            "customer_id": customer.id,
                            "customer_name": customer.name,
                            "doc_type": "crm_interaction",
                            "category": "CRM Note",
                            "source": inter.channel,
                            "date": inter.date,
                            "rm_name": inter.rm_name,
                            "tags": inter.tags,
                        },
                    ),
                    index=idx,
                )
            )

        # 3. Commitments
        for idx, com in enumerate(customer.commitments):
            com_text = (
                f"Relationship Commitment/Discussion: {com.title}\n"
                f"Classification: {com.commitment_type.value.upper()}\n"
                f"Status: {com.status.value.upper()}\n"
                f"Promised By: {com.committed_by} on {com.committed_on}\n"
                f"Details: {com.details}\n"
                f"Evidence: {com.evidence_snippet or 'None'}"
            )
            chunks.append(
                Chunk(
                    id=f"{customer.id}_com_{com.id}",
                    content=com_text,
                    metadata=ServiceMetadata(
                        service="saathi",
                        document_type=DocumentType.OTHER,
                        source="Commitment Register",
                        file_path=f"saathi/{customer.id}/commitments/{com.id}.txt",
                        extra={
                            "customer_id": customer.id,
                            "customer_name": customer.name,
                            "doc_type": "commitment",
                            "category": "Commitment",
                            "source": "Commitment Register",
                            "commitment_type": com.commitment_type.value,
                            "status": com.status.value,
                        },
                    ),
                    index=idx,
                )
            )

        # 4. Verified Facts & Nuances
        for idx, fact in enumerate(customer.facts):
            fact_text = (
                f"Customer Fact ({fact.category}):\n"
                f"Statement: {fact.statement}\n"
                f"Status: {fact.status.value.upper()} | Last Updated: {fact.last_updated}"
            )
            chunks.append(
                Chunk(
                    id=f"{customer.id}_fact_{fact.id}",
                    content=fact_text,
                    metadata=ServiceMetadata(
                        service="saathi",
                        document_type=DocumentType.OTHER,
                        source="Customer Memory",
                        file_path=f"saathi/{customer.id}/facts/{fact.id}.txt",
                        extra={
                            "customer_id": customer.id,
                            "customer_name": customer.name,
                            "doc_type": "customer_fact",
                            "category": fact.category,
                            "source": "Customer Memory",
                            "status": fact.status.value,
                        },
                    ),
                    index=idx,
                )
            )

        # 5. Timeline Events
        for idx, event in enumerate(customer.timeline):
            event_text = (
                f"Relationship Milestone ({event.date_display}): {event.title}\n"
                f"Description: {event.description}\n"
                f"Category: {event.category} | Source: {event.source_channel}"
            )
            chunks.append(
                Chunk(
                    id=f"{customer.id}_time_{event.id}",
                    content=event_text,
                    metadata=ServiceMetadata(
                        service="saathi",
                        document_type=DocumentType.OTHER,
                        source=event.source_channel,
                        file_path=f"saathi/{customer.id}/timeline/{event.id}.txt",
                        extra={
                            "customer_id": customer.id,
                            "customer_name": customer.name,
                            "doc_type": "timeline_event",
                            "category": event.category,
                            "source": event.source_channel,
                            "date": event.date_display,
                        },
                    ),
                    index=idx,
                )
            )

        # 6. Manual Relationship Context (Added from UI)
        for idx, note in enumerate(customer.extra_context):
            note_text = (
                f"Manual RM Relationship Note: {note.title}\n"
                f"Category: {note.category} | Channel: {note.source_channel}\n"
                f"Recorded By: {note.recorded_by} on {note.created_at}\n"
                f"Context Content:\n{note.content}"
            )
            chunks.append(
                Chunk(
                    id=f"{customer.id}_ctx_{note.id}",
                    content=note_text,
                    metadata=ServiceMetadata(
                        service="saathi",
                        document_type=DocumentType.OTHER,
                        source=note.source_channel,
                        file_path=f"saathi/{customer.id}/context/{note.id}.txt",
                        extra={
                            "customer_id": customer.id,
                            "customer_name": customer.name,
                            "doc_type": "manual_context",
                            "category": note.category,
                            "source": note.source_channel,
                            "recorded_by": note.recorded_by,
                            "date": note.created_at,
                        },
                    ),
                    index=idx,
                )
            )

        return chunks

    async def index_customer(self, customer: CustomerRelationship, force: bool = False) -> int:
        """
        Embeds and upserts all relationship context for a given customer into the
        dedicated Saathi Qdrant collection.
        """
        chunks = self._build_customer_chunks(customer)
        if not chunks:
            return 0

        content_fingerprint = hashlib.sha256(
            "".join(c.content for c in chunks).encode("utf-8")
        ).hexdigest()

        if not force and self._indexed_customer_hashes.get(customer.id) == content_fingerprint:
            logger.debug(f"Customer '{customer.id}' already up-to-date in Saathi vector store.")
            return 0

        logger.info(
            f"Embedding and indexing {len(chunks)} chunks for customer '{customer.name}' "
            f"into collection '{self.settings.qdrant_saathi_collection_name}'..."
        )
        texts = [c.content for c in chunks]
        embeddings = await self.embedding_provider.embed(texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        count = await self.vector_store.upsert(chunks)
        self._indexed_customer_hashes[customer.id] = content_fingerprint
        logger.info(f"Successfully upserted {count} chunks for customer '{customer.id}'.")
        return count

    async def index_single_context(
        self,
        customer_id: str,
        customer_name: str,
        item: ManualContextItem,
    ) -> int:
        """
        Efficiently embeds and indexes a single new manually added context note.
        """
        note_text = (
            f"Manual RM Relationship Note: {item.title}\n"
            f"Category: {item.category} | Channel: {item.source_channel}\n"
            f"Recorded By: {item.recorded_by} on {item.created_at}\n"
            f"Context Content:\n{item.content}"
        )
        chunk = Chunk(
            id=f"{customer_id}_ctx_{item.id}",
            content=note_text,
            metadata=ServiceMetadata(
                service="saathi",
                document_type=DocumentType.OTHER,
                source=item.source_channel,
                file_path=f"saathi/{customer_id}/context/{item.id}.txt",
                extra={
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "doc_type": "manual_context",
                    "category": item.category,
                    "source": item.source_channel,
                    "recorded_by": item.recorded_by,
                    "date": item.created_at,
                },
            ),
        )

        embeddings = await self.embedding_provider.embed([chunk.content])
        chunk.embedding = embeddings[0]
        count = await self.vector_store.upsert([chunk])
        self._indexed_customer_hashes.pop(customer_id, None)
        return count

    async def search_customer_context(
        self,
        customer_id: str,
        query: str,
        limit: int = 6,
    ) -> List[Chunk]:
        """
        Semantic vector search strictly pre-filtered by customer_id to guarantee data isolation.
        """
        try:
            query_embeddings = await self.embedding_provider.embed([query])
            query_vector = query_embeddings[0]

            results = await self.vector_store.search(
                query_vector=query_vector,
                limit=limit,
                filter_dict={"customer_id": customer_id},
            )
            return results
        except Exception as e:
            logger.error(f"Error searching Saathi customer context: {e}")
            return []

    async def get_all_customer_context_text(
        self,
        customer_id: str,
        fallback_customer: Optional[CustomerRelationship] = None,
    ) -> str:
        """
        Retrieves all context chunks for a customer to synthesize the full relationship brief.
        If Qdrant search returns chunks, compiles them; otherwise formats the customer model.
        """
        chunks = await self.search_customer_context(
            customer_id=customer_id,
            query="customer relationship background family priorities commitments banking preferences",
            limit=25,
        )

        if chunks:
            parts = []
            for c in chunks:
                category = c.metadata.extra.get("category", "")
                source = c.metadata.extra.get("source", "")
                parts.append(f"[{category} | Source: {source}]\n{c.content}")
            return "\n\n".join(parts)

        if fallback_customer:
            lines = [
                f"Client: {fallback_customer.name} ({fallback_customer.tier.value}, AUM: {fallback_customer.aum_display})",
                f"Previous RM: {fallback_customer.previous_rm_name} | Incoming RM: {fallback_customer.new_rm_name}",
            ]
            for inter in fallback_customer.interactions:
                lines.append(f"- CRM [{inter.date} {inter.channel}]: {inter.summary}")
            for com in fallback_customer.commitments:
                lines.append(f"- Commitment [{com.commitment_type.value}]: {com.title} - {com.details}")
            for f in fallback_customer.facts:
                lines.append(f"- Fact [{f.category}]: {f.statement}")
            for ctx in fallback_customer.extra_context:
                lines.append(f"- Manual Context [{ctx.category} by {ctx.recorded_by}]: {ctx.title} - {ctx.content}")
            return "\n".join(lines)

        return ""


_saathi_indexer: Optional[SaathiIndexer] = None


def get_saathi_indexer() -> SaathiIndexer:
    global _saathi_indexer
    if _saathi_indexer is None:
        _saathi_indexer = SaathiIndexer()
    return _saathi_indexer
