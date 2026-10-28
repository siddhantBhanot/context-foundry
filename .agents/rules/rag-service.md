---
trigger: glob
globs: rag_service/**
---

# RAG Service Rules

## 1. Service Responsibility

`rag_service` owns the Retrieval-Augmented Generation pipeline.

It is responsible for:

-   Knowledge ingestion
-   Document loading
-   Chunking
-   Metadata generation
-   Embedding
-   Vector storage
-   Retrieval
-   Context assembly
-   Prompt construction
-   LLM interaction
-   Source/provenance handling

Keep RAG-specific implementation out of the frontend.

------------------------------------------------------------------------

# 2. Technology Stack

Use:

-   Python 3.12+
-   Qdrant Cloud (primary vector storage with payload filtering)
-   Qdrant FastEmbed (`sentence-transformers/all-MiniLM-L6-v2`, 384-dim) for fast local embeddings with zero cloud API keys
-   Groq Cloud (OpenAI-compatible high-speed inference) as primary LLM provider
-   LlamaIndex Core
-   PyPDF for document parsing
-   AWS Bedrock (optional fallback/alternative provider, not required)

The RAG implementation must remain strictly provider-independent at the
application boundary.

Future providers may include:

-   Google Gemini
-   Groq Cloud
-   Other OpenAI-compatible or hosted providers

When generating LlamaIndex components, ensure compatibility with the
current `rag_service` environment and installed package versions.

------------------------------------------------------------------------

# 3. Provider Abstraction

External providers must be abstracted behind interfaces.

For example:

``` python
class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[Message],
        **kwargs
    ) -> LLMResponse:
        ...
```

Implementations may include:

``` text
GroqLLMProvider (primary active provider, e.g. openai/gpt-oss-120b)
BedrockLLMProvider (optional fallback)
GeminiLLMProvider (optional)
```

Embedding providers should follow a similar boundary:

``` python
class EmbeddingProvider(Protocol):
    async def embed(
        self,
        texts: list[str]
    ) -> list[list[float]]:
        ...
```

Active implementation:

``` text
FastEmbedProvider (sentence-transformers/all-MiniLM-L6-v2, 384 dimensions)
BedrockEmbeddingProvider (optional fallback)
```

Vector storage must also be abstracted:

``` python
class VectorStore(Protocol):
    async def upsert(...):
        ...

    async def search(...):
        ...

    async def delete(...):
        ...
```

Initial implementation:

``` text
QdrantVectorStore
```

Changing a provider should not require rewriting the RAG application
logic.

------------------------------------------------------------------------

# 4. RAG Pipeline

Keep the RAG pipeline modular.

The conceptual pipeline is:

``` text
User Query
    ↓
Query Processing
    ↓
Metadata Filtering
    ↓
Retrieval
    ↓
Optional Reranking
    ↓
Context Assembly
    ↓
Prompt Construction
    ↓
LLM Provider
    ↓
Grounded Response
    ↓
Sources / Citations
```

Each stage must have a clearly defined responsibility.

Do not create one large function containing ingestion, embedding,
retrieval, prompting, LLM calls, logging, and response formatting.

------------------------------------------------------------------------

# 5. Knowledge Scope & Supported Formats

The platform supports dynamic, multi-microservice knowledge bases.
Users can create new microservices and ingest code and documentation on demand.

Supported Ingestion Formats:

1.  **Kotlin Source Code (`.kt`, `.kts`)**:
    Parsed via `KotlinChunker`, extracting package, class, interface, method,
    annotations, and exact line ranges (`#L{start}-L{end}`).

2.  **Markdown Documentation (`.md`, `.markdown`)**:
    Parsed via `MarkdownChunker`, preserving heading hierarchy (`#`, `##`, `###`),
    code blocks, and section context.

3.  **PDF Documents (`.pdf`)**:
    Parsed via `PyPDF`, formatted into paginated Markdown (`## Page N`), and
    processed into contextual chunks.

4.  **ZIP Archives (`.zip`)**:
    Unpacked safely (with zip-bomb byte/entry checks and path traversal protection),
    recursively extracting all inner `.kt`, `.kts`, `.md`, and `.pdf` files.

Every chunk must be tagged with its corresponding `service` identifier.

------------------------------------------------------------------------

# 6. Knowledge Isolation

All indexed knowledge must contain service-level metadata.

At minimum:

``` text
service
document_type
source
file_path
language
```

Where available, also capture:

``` text
class
method
endpoint
integration
git_commit
version
```

For the initial knowledge base:

``` text
service = income-assessment-service
```

Retrieval must support service-level filtering.

Prefer logical isolation using metadata, collections, or namespaces
rather than creating a separate vector database for every microservice.

------------------------------------------------------------------------

# 7. Markdown Ingestion

Markdown documentation is curated engineering knowledge.

The ingestion pipeline should:

1.  Load Markdown files.
2.  Preserve document metadata.
3.  Split documents into semantically meaningful chunks.
4.  Generate embeddings.
5.  Store vectors and metadata in Qdrant.

Prefer semantic boundaries:

``` text
Document
 → Heading
 → Subheading
 → Paragraph / code block
```

Chunks should contain enough context to be independently understandable.

Avoid:

-   Arbitrarily splitting related content
-   Extremely small chunks that lose context
-   Extremely large chunks that reduce retrieval precision
-   Keyword stuffing solely for embeddings

Documentation should be written for both humans and semantic retrieval.

------------------------------------------------------------------------

# 8. Kotlin Source Code Ingestion

The `income-assessment-service` source code is written in Kotlin/Spring
Boot.

Preserve metadata such as:

``` text
service: income-assessment-service
document_type: source_code
language: kotlin
file_path: ...
package: ...
class_name: ...
method_name: ...
```

Where possible, preserve relevant:

-   Spring annotations
-   Controllers
-   Services
-   Repositories
-   Integration clients
-   Configuration
-   Functions/classes

Prefer code-aware chunking that preserves logical units.

Do not introduce sophisticated AST/Tree-sitter parsing unless there is a
demonstrated MVP requirement.

------------------------------------------------------------------------

# 9. Retrieval Strategy

The initial retrieval strategy should prioritize correctness and
simplicity.

Use:

-   Semantic vector search
-   Metadata filtering
-   Source provenance

Design the retrieval layer so that future improvements can be added
independently:

-   Keyword/BM25 search
-   Hybrid retrieval
-   Reranking
-   Query rewriting
-   Multi-query retrieval

Do not implement these prematurely.

------------------------------------------------------------------------

# 10. Grounded Responses

LLM responses must be grounded in retrieved knowledge.

The system prompt must instruct the model to:

-   Not invent implementation details.
-   Not claim something exists when it is absent from retrieved context.
-   Prefer source code/documentation over assumptions.
-   Clearly state when the available knowledge is insufficient.
-   Cite relevant sources where possible.

Source references must come from actual retrieved documents/chunks.

Never fabricate citations.

------------------------------------------------------------------------

# 11. Conversation Context

The LLM API must not be assumed to retain memory between calls.

The application must explicitly provide relevant conversation history.

For the MVP:

``` text
System Prompt
+
Relevant Conversation History
+
Retrieved RAG Context
+
Current User Question
```

Do not send unlimited conversation history.

The query-processing layer should be designed so query rewriting can be
added later for follow-up questions such as:

> What happens after that?

------------------------------------------------------------------------

# 12. Prompt Management

Prompts must be centralized and version-controlled.

Prefer:

``` text
prompts/
├── system.md
├── query_answer.md
└── ...
```

Do not scatter prompt strings throughout route handlers or unrelated
services.

Prompts should clearly define:

-   Role
-   Grounding requirements
-   Source usage
-   Hallucination behavior
-   Expected answer format

Provider-specific adaptations should remain inside provider adapters
where necessary.

------------------------------------------------------------------------

# 13. Configuration

Provider and model selection must be configuration-driven.

Examples:

``` text
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_STORE=qdrant
QDRANT_URL=https://<cluster-id>.aws.cloud.qdrant.io:6333
QDRANT_COLLECTION=engineering_knowledge_base
```

Do not hardcode provider credentials, URLs, or model configuration.

------------------------------------------------------------------------

# 14. Audit and Retrieval Metadata

Where appropriate, record:

``` text
timestamp
request_id
service
query
retrieved sources
provider
model
latency
status
```

Avoid storing full prompts/responses when they may contain sensitive
information unless explicitly required and approved.

------------------------------------------------------------------------

# 15. RAG Evaluation

Maintain a small curated evaluation set of real developer questions.

Each evaluation case should ideally contain:

``` text
Question
Expected answer characteristics
Expected source(s)
```

Prioritize retrieval correctness and source grounding over superficial
answer fluency.

A lightweight custom evaluation suite is sufficient for the MVP.
Additional evaluation frameworks can be introduced later if useful.