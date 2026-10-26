# ContextFoundry

> **Autonomous Engineering Intelligence & Context Continuity Platform**  
> *A high-performance, multi-tenant Retrieval-Augmented Generation (RAG) platform bridging technical microservice knowledge and organizational relationship memory.*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![LlamaIndex](https://img.shields.io/badge/LlamaIndex-0.12+-purple.svg)](https://www.llamaindex.ai)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red.svg?logo=qdrant)](https://qdrant.tech)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)

---

## 🌟 Executive Overview

**ContextFoundry** is an enterprise-grade Knowledge Intelligence platform designed to solve the critical problem of tribal knowledge silos, slow developer onboarding, and lost operational context.

The platform provides two dedicated, persona-tailored workspaces powered by a unified RAG engine:

1. **Dev Central (Engineering Intelligence Hub)**:
   - **Interactive Microservice Chat**: Grounded Q&A against source code, APIs, and architectural decisions with exact markdown citations.
   - **Knowledge Cafe**: University-style interactive training courses featuring module syllabi, lesson progression, doubt-clearing AI assistants, and automated quizzes.
   - **Dynamic Architecture Diagrams**: Automatically generates interactive Mermaid sequence flows and entity diagrams from retrieved system context.
   - **Self-Service Ingestion**: Drag-and-drop document ingestion supporting PDF, Markdown, and source code.

2. **Saathi (Relationship Continuity Engine)**:
   - **Client Relationship Continuity**: Preserves institutional memory when advisors or relationship managers transition accounts.
   - **Pre-Call Briefings & Executive Summaries**: AI-synthesized client dossiers, risk profiles, open commitments, and past interaction timelines.
   - **Context Validation**: Customer validation workflow allowing clients to review and confirm relationship priorities.

---

## 🏛️ System Architecture

```mermaid
graph TD
    subgraph Presentation_Layer ["Frontend Workspace (React 19 + TypeScript + Tailwind)"]
        UI_Dev["Dev Central<br/>• Code Chat & Ingestion<br/>• Knowledge Cafe (Courses & Quizzes)<br/>• Dynamic Mermaid Diagrams"]
        UI_Saathi["Saathi Workspace<br/>• Client Dossier & Timelines<br/>• Pre-Call AI Briefings<br/>• Handover Continuity Engine"]
    end

    subgraph API_Layer ["Backend Gateway (FastAPI + Async Python)"]
        Auth["JWT Auth & Role-Based Access Control"]
        DirectAdapter["Direct RAG Client Adapter"]
        SQLiteRepo["Async Persistence (SQLite / aiosqlite)"]
    end

    subgraph RAG_Engine ["RAG & Ingestion Engine (LlamaIndex + Multi-Provider)"]
        Chunker["AST & Markdown Chunkers (Kotlin, MD, PDF)"]
        Embedder["Embedding Provider<br/>• AWS Bedrock Titan v2<br/>• Local/Mock Embeddings"]
        FallbackLLM["Multi-Provider LLM Fallback Engine<br/>1. AWS Bedrock (Claude 3.5 / Sonnet 4.6)<br/>2. Groq Cloud (Llama 3.3 70B Versatile)<br/>3. OpenAI (GPT-4o)"]
    end

    subgraph Vector_Storage ["Vector Database (Qdrant)"]
        QdrantStore["Qdrant Cloud / Local Cluster<br/>• Tenant-Isolated Vector Collections<br/>• Payload Filtering by Service / Customer"]
    end

    UI_Dev -->|HTTP / SSE Streaming| API_Layer
    UI_Saathi -->|HTTP / SSE Streaming| API_Layer
    Auth --> DirectAdapter
    DirectAdapter --> RAG_Engine
    Chunker --> Embedder
    Embedder --> QdrantStore
    QdrantStore --> FallbackLLM
    FallbackLLM -->|Streamed Tokens| DirectAdapter
```

---

## 🚀 Key Technical Highlights

- **Multi-Provider LLM Resilience**: Dynamic multi-provider orchestration with automatic fallback between AWS Bedrock, Groq Cloud, and OpenAI to eliminate vendor lock-in and handle rate limits.
- **Tenant-Isolated Vector Storage**: Segmented retrieval pipelines utilizing Qdrant payload filters, guaranteeing strict isolation between services and customer dossiers.
- **Real-Time Token Streaming**: Server-Sent Events (SSE) streaming with low time-to-first-token (TTFT) and citation attribution.
- **Code & Markdown AST Parsing**: Custom chunkers that respect function boundaries and document section headers rather than splitting mid-token.
- **Clean Hexagonal Architecture**: Modular separation between Presentation, Application, Domain, and Infrastructure adapters.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons, Mermaid.js, React Markdown |
| **Backend API** | FastAPI, Python 3.12, Pydantic v2, Pydantic-Settings, aiosqlite, Uvicorn |
| **RAG & Search** | LlamaIndex Core, Qdrant Client, Groq SDK, Boto3 (Bedrock), PyPDF |
| **Vector DB** | Qdrant (Cloud / Local Container) |
| **DevOps & Containers** | Docker, Docker Compose, Nginx (Alpine) |

---

## ⚡ Quickstart Guide

### Option 1: One-Command Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/<your-username>/context-foundry.git
   cd context-foundry
   ```

2. Copy the environment template:
   ```bash
   cp .env.example .env
   # Add your GROQ_API_KEY (free tier available at console.groq.com)
   ```

3. Launch all services:
   ```bash
   docker compose up --build
   ```

4. Access the applications:
   - **Web UI**: [http://localhost:3000](http://localhost:3000)
   - **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Qdrant Vector Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

### Option 2: Local Development Setup

#### 1. Backend & RAG Service
```bash
# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend_service/requirements.txt
pip install -r rag_service/requirements.txt

# Configure environment
cp .env.example .env

# Run FastAPI backend
python -m uvicorn backend_service.app.main:app --reload --port 8000
```

#### 2. Frontend Service
```bash
cd frontend-service

# Install dependencies
npm install

# Start Vite dev server
npm run dev
# Accessible at http://localhost:5173
```

---

## 🧪 Quick Demo Logins

The application includes built-in demo credentials for quick persona exploration:

| Persona | Demo Email | Workspace | Description |
| :--- | :--- | :--- | :--- |
| **Software Engineer** | `engineer@contextfoundry.dev` | **Dev Central** | Explore architecture docs, ask RAG questions, and browse Knowledge Cafe courses. |
| **Client Advisor** | `advisor@contextfoundry.dev` | **Saathi** | Explore client dossiers, pre-call briefs, timeline records, and handover memory. |

---

## 💼 Portfolio Highlights & Resume Summary

> **ContextFoundry — Autonomous Engineering Intelligence & Multi-Tenant Knowledge Platform**
> - Architected a production-ready, dual-persona RAG platform serving software engineering teams and client relationship managers.
> - Implemented an intelligent multi-provider LLM orchestration layer (AWS Bedrock, Groq, OpenAI) with automatic fallback and sub-second token streaming.
> - Designed tenant-isolated vector retrieval with Qdrant, supporting structured AST-aware chunking of source code, Markdown, and technical specifications.
> - Built a responsive React 19 / TypeScript frontend featuring interactive courses, automated quizzes, live Markdown formatting, and automated Mermaid diagram rendering.
> - Containerized the entire multi-service stack using multi-stage Docker builds and Docker Compose for zero-friction local and cloud deployments.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
