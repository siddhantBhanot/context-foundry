---
trigger: glob
globs: frontend-service/**
---

# Frontend Service Rules

## 1. Scope

`frontend-service` is the developer-facing web application for the
ContextFoundry Engineering Intelligence Platform.

It supports:

-   Dynamic microservice selection and creation
-   Source code (.kt, .kts) and documentation (.md, .pdf, .zip) ingestion
-   Microservice-grounded streaming chat with exact line citations
-   Interactive Knowledge Cafe: course enrollment, lesson synthesis, doubt drawer, and tutorial authoring

The frontend must communicate with the backend API only. Never call
Qdrant, Groq, Bedrock, or other privileged infrastructure directly from
the browser.

------------------------------------------------------------------------

## 2. Stack

Use:

-   React 19
-   TypeScript (strict typing, avoid `any`)
-   Vite
-   Tailwind CSS v4
-   Lucide React & Mermaid.js
-   React Markdown & Syntax Highlighter

Prefer functional components and clean React hooks.

Do not add unnecessary libraries or frameworks.

------------------------------------------------------------------------

## 3. UI / UX

The application should feel like a clean, high-performance
**engineering intelligence tool**, not a generic AI chatbot.

Visual aesthetic:

-   Palette: Warm developer orange (`#f05a28`), modern slate tones, clean dark accents
-   Clean, minimal information density with clear typography
-   Subtle micro-animations, fast transitions, and instant feedback
-   First-class code presentation: syntax highlighting, file paths, line ranges, and auto-rendered Mermaid diagrams
-   Grounded source citation cards allowing users to view the exact ingested source code or document snippet in a modal

The primary layout provides two dedicated modes:
1. **Dev Central Chat**: Interactive conversational code & architecture exploration
2. **Knowledge Cafe**: Structured onboarding curricula, module roadmaps, live quizzes, and tutorial creation

------------------------------------------------------------------------

## 4. Authentication

Implement:

-   Signup
-   Login
-   Logout
-   Session persistence
-   Protected application routes

Keep authentication behind a simple reusable abstraction such as:

``` text
useAuth()
```

Components should not depend on authentication implementation details.

Never expose backend, AWS, Qdrant, or LLM credentials in frontend code.

------------------------------------------------------------------------

## 5. Application Layout

After login, use a simple layout:

``` text
Header
├── Product / Logo
└── User / Logout

Sidebar
├── New Chat
└── Conversation History

Main
└── Chat Interface
```

The sidebar may be collapsible.

The chat experience must remain the primary focus.

------------------------------------------------------------------------

## 6. Service Selector & Dynamic Management

Provide a microservice dropdown with dynamic creation capabilities.

Default initial service:

``` text
income-assessment-service
```

Users must be able to:
- Select any active microservice from the dropdown.
- Add a new microservice dynamically via "+ New Microservice" in the header or ingestion modal.
- Upload code and documentation (.kt, .kts, .md, .pdf, .zip) targeted specifically at that microservice.
- View staged files vs indexed files, with clear status indicators.
- Trigger ingestion and clean re-indexing.

Prefer a centralized model:

``` typescript
export interface Microservice {
  id: string;
  name: string;
  description?: string;
  has_indexed_data?: boolean;
  doc_count?: number;
}
```

The selected service must be included in every chat query sent to the backend.

------------------------------------------------------------------------

## 7. API Client

Do not make raw `fetch()` calls throughout React components.

Create a centralized API layer:

``` text
lib/
└── api/
    ├── client.ts
    ├── auth.ts
    ├── chat.ts
    ├── feedback.ts
    └── knowledge.ts
```

Components should use typed functions such as:

``` text
login()
signup()
queryService()
submitFeedback()
addKnowledge()
```

Keep API response/request types explicit.

------------------------------------------------------------------------

## 8. Chat API and SSE Streaming

Primary endpoint:

``` text
POST /api/v1/query/stream
```

Chat responses must stream using **Server-Sent Events (SSE)**.

Because the endpoint is POST, use:

``` text
fetch()
+
ReadableStream
```

for the primary implementation.

Render incoming content progressively. Do not wait for the complete
response.

Use `AbortController` to support cancellation.

------------------------------------------------------------------------

## 9. Generation State

While a response is streaming:

-   Disable normal submit actions.
-   Prevent duplicate requests.
-   Show a clear generating state.
-   Display a visible `Stop Generating` button.
-   Allow the user to cancel the request.

Use explicit message states where useful:

``` typescript
type MessageStatus =
  | "pending"
  | "streaming"
  | "complete"
  | "error"
  | "cancelled";
```

After cancellation or failure, return the UI to a usable state.

------------------------------------------------------------------------

## 10. Error Handling

Gracefully handle:

-   4xx responses
-   5xx responses
-   Backend disconnection
-   Network errors
-   SSE/stream errors
-   Timeouts
-   User cancellation
-   Partial responses

Never allow a failed request to crash the React component tree.

Show a useful error message and provide:

``` text
[ Retry ]
```

where appropriate.

Retry should reuse the original query, service, and conversation
context.

Use Next.js/React error boundaries for unexpected rendering errors.

------------------------------------------------------------------------

## 11. Chat Rendering

Assistant responses must support:

-   Markdown
-   Headings
-   Lists
-   Tables
-   Inline code
-   Code blocks
-   Links

Code blocks should have:

-   Syntax highlighting
-   Copy button
-   Horizontal scrolling
-   Language labels where available

Kotlin code must render correctly.

------------------------------------------------------------------------

## 12. Source Citations

Source citations are a core feature.

Each grounded response should display sources returned by the backend.

Example:

``` text
Sources

ApplicationController.kt
src/.../ApplicationController.kt

initiation-application.md
knowledge/api/initiation-application.md
```

Where available, display:

-   File
-   Document type
-   Class
-   Method
-   Endpoint
-   Line number

Only display source metadata returned by the backend.

Never fabricate citations.

------------------------------------------------------------------------

## 13. Source Viewer

Where practical, provide a `View Source` action.

Opening a source should show the relevant:

-   Kotlin code or Markdown
-   File path
-   Class/method information
-   Relevant section

Use a drawer/panel/modal rather than navigating away from the
conversation.

Keep this component reusable.

------------------------------------------------------------------------

## 14. Conversation History

Support multiple conversations.

MVP functionality:

-   New conversation
-   Continue existing conversation
-   View previous messages

Rename/delete can be added if time permits.

Starting a new conversation should clear the current chat while
preserving the selected service.

The frontend should not assume that the LLM remembers previous
conversations.

------------------------------------------------------------------------

## 15. Suggested Questions

Show a small set of useful questions on an empty/new chat.

Examples:

``` text
What is the business handler for FOUR_WHEELER_PERSONAL?

What API contract is currently used for /initiation-application?

What is the request flow from the UI to the backend?

What happens after /generate-link is called?

Which services integrate with CAP?
```

Clicking a suggestion should populate or submit the query.

------------------------------------------------------------------------

## 16. Feedback

Each completed assistant response should provide:

``` text
👍
👎
```

Send feedback through:

``` text
POST /api/feedback
```

Associate feedback with the relevant conversation/message/query/service.

For negative feedback, an optional short reason may be provided.

Keep feedback unobtrusive.

------------------------------------------------------------------------

## 17. Microservice Knowledge Ingestion & Re-indexing

Provide an `IngestionModal` workflow for microservice knowledge management:

1. **Target Microservice**:
   - Current active microservice pre-selected.
   - Quick action to create a new microservice context on the fly.

2. **Supported File Formats**:
   - Kotlin source files (`.kt`, `.kts`)
   - Markdown documents (`.md`, `.markdown`)
   - PDF documents (`.pdf`)
   - ZIP archives containing code and documentation (`.zip`)

3. **Staging & Review**:
   - Drag-and-drop or file picker with format validation.
   - List of staged files with file size, extension badge, and individual removal.
   - Comparison of staged vs currently indexed files.

4. **Actions**:
   - `Ingest Staged Files`: Triggers semantic chunking, embedding via FastEmbed, and upserting vectors into Qdrant Cloud under `service == service_id`.
   - `Clear & Re-index`: Wipes all existing Qdrant points for this microservice and re-indexes the uploaded files from scratch.

5. **Progress & Feedback**:
   - Real-time progress indicators: `Uploading...`, `Chunking & Embedding...`, `Completed`.
   - Empty-state banner on main chat when a service has `doc_count === 0`, guiding users to upload files.

------------------------------------------------------------------------

## 18. Loading and Empty States

Every asynchronous operation must have a clear UI state.

Examples:

``` text
Loading conversation...
Generating response...
Submitting feedback...
Adding to knowledge base...
```

The empty chat screen should explain what users can ask and show
suggested questions.

Avoid blank screens.

------------------------------------------------------------------------

## 19. State Management

Use React state/hooks for local state.

Do not introduce Redux or another global state framework for the MVP.

Keep these concerns separate:

-   Authentication state
-   Conversation state
-   Streaming state
-   UI state
-   Server state

Do not put all state into one global store.

------------------------------------------------------------------------

## 20. Component Structure

Prefer small, reusable components.

Suggested structure:

``` text
components/
├── chat/
│   ├── ChatWindow.tsx
│   ├── ChatMessage.tsx
│   ├── ChatInput.tsx
│   ├── StreamingMessage.tsx
│   ├── SourceList.tsx
│   └── SuggestedQuestions.tsx
│
├── layout/
│   ├── Header.tsx
│   ├── Sidebar.tsx
│   └── AppLayout.tsx
│
├── auth/
│   ├── LoginForm.tsx
│   └── SignupForm.tsx
│
├── knowledge/
│   └── AddToKnowledgeBase.tsx
│
└── common/
    ├── LoadingState.tsx
    └── ErrorState.tsx
```

Do not create a single component containing the entire application.

------------------------------------------------------------------------

## 21. Performance

Prioritize perceived performance.

Use streaming so response content appears as soon as possible.

Avoid unnecessary React re-renders during streaming.

If required, batch streamed updates instead of updating React state for
every token.

Do not add complex caching/performance infrastructure for the MVP.

------------------------------------------------------------------------

## 22. Security

Never expose:

-   AWS credentials
-   Qdrant API keys
-   Bedrock credentials
-   Gemini API keys
-   Groq API keys
-   Backend secrets

Do not place privileged secrets in `NEXT_PUBLIC_*` variables.

All privileged operations must go through the backend.

Render backend-provided Markdown safely. Do not render untrusted HTML
without sanitization.

------------------------------------------------------------------------

## 23. Environment Configuration

Use environment variables for frontend configuration.

Example:

``` text
NEXT_PUBLIC_API_BASE_URL
```

Do not hardcode backend URLs.

Provide `.env.example`.

Never commit `.env` files containing secrets.

------------------------------------------------------------------------

## 24. Docker

The frontend must be Dockerized.

Prefer a multi-stage Docker build.

Docker Compose should run the frontend with the other local application
services.

Do not hardcode `localhost` for backend communication inside the Docker
network.

Use environment-based configuration.

------------------------------------------------------------------------

## 25. MVP Discipline

Keep the frontend simple and focused on the demo.

Do NOT introduce:

-   Redux
-   GraphQL
-   WebSockets
-   Micro-frontends
-   Complex state machines
-   Multiple UI frameworks
-   Large design systems

SSE is the required streaming protocol.

Prioritize:

1.  Authentication
2.  Excellent chat UX
3.  SSE streaming
4.  Source citations
5.  Service selector
6.  Conversation history
7.  Feedback
8.  Dockerized local execution

Features such as source viewer, conversation rename/delete, and advanced
ingestion status are secondary if time is limited.

------------------------------------------------------------------------

## 26. Knowledge Cafe & Tutorial Authoring

Knowledge Cafe serves as the structured onboarding and learning environment for developers and teams.

Key capabilities:
1. **Curriculum Browsing**:
   - Filter tutorials by target microservice or difficulty (Beginner, Intermediate, Advanced).
   - Display completion status, enrolled timestamp, and quiz scores.

2. **Interactive Lesson Studio**:
   - Progressive lesson content synthesis streamed via SSE.
   - Live Mermaid diagram generation for architectural flows.
   - In-lesson doubt drawer (`POST /api/v1/kt/courses/{id}/lessons/{id}/doubts/stream`) allowing contextual follow-ups without leaving the lesson.
   - Interactive end-of-lesson knowledge-check quizzes with immediate feedback.

3. **Tutorial Creation & Publishing**:
   - Form-based creator allowing users and team members to author custom courses.
   - Define course title, description, target microservice, difficulty, and structured modules/lessons.
   - Interactive quiz editor for multiple-choice questions with answer explanations.
   - Direct publication to `knowledge_cafe_collection` via `POST /api/v1/kt/courses`.

