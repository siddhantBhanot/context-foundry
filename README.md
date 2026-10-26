# ContextFoundry

> **Autonomous Engineering Intelligence Platform for Microservices**  
> *A high-performance, production-ready Retrieval-Augmented Generation (RAG) platform bridging technical microservice codebases, architectural knowledge, and developer onboarding.*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![LlamaIndex](https://img.shields.io/badge/LlamaIndex-0.12+-purple.svg)](https://www.llamaindex.ai)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red.svg?logo=qdrant)](https://qdrant.tech)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)

---

## 🌟 Executive Overview

**ContextFoundry** is an enterprise-grade Engineering Intelligence platform designed to eradicate tribal knowledge silos, accelerate developer onboarding, and provide instant, verified answers across complex microservice architectures.

Key capabilities include:

- **Interactive Microservice Chat**: Grounded Q&A against source code, APIs, and architectural decisions with exact line-level markdown citations.
- **Knowledge Cafe (Interactive KT)**: Structured onboarding curriculum featuring module syllabi, lesson progression, doubt-clearing AI assistants, and automated quizzes.
- **Dynamic Architecture Diagrams**: Automatically generates and renders interactive Mermaid sequence flows and entity relationship diagrams from retrieved code context.
- **Self-Service Ingestion**: Drag-and-drop document and codebase ingestion supporting ZIP archives, PDF, Markdown, and source code with AST-aware chunking.
- **Conversation Management & Sharing**: Multi-turn conversation history drawer, shareable read-only links, and granular feedback controls.

---

## 🏛️ System Architecture

```mermaid
graph TD
    subgraph Presentation_Layer ["Frontend Workspace (React 19 + TypeScript + Tailwind)"]
        UI_Dev["Dev Central<br/>• Codebase & Architecture Chat<br/>• Knowledge Cafe (Courses & Quizzes)<br/>• Dynamic Mermaid Diagrams<br/>• Self-Service Ingestion Modal"]
    end

    subgraph API_Layer ["Backend Gateway (FastAPI + Async Python)"]
        Auth["JWT Auth & Role-Based Access Control"]
        DirectAdapter["Direct RAG Client Adapter"]
        SQLiteRepo["Async Persistence (SQLite / aiosqlite)"]
    end

    subgraph RAG_Engine ["RAG & Ingestion Engine (LlamaIndex + Multi-Provider)"]
        Chunker["AST & Markdown Chunkers (Kotlin, Python, MD, PDF)"]
        Embedder["Embedding Provider<br/>• AWS Bedrock Titan v2<br/>• FastEmbed / Local Embeddings"]
        FallbackLLM["Multi-Provider LLM Fallback Engine<br/>1. AWS Bedrock (Claude 3.5 / Sonnet 4.6)<br/>2. Groq Cloud (Llama 3.3 70B Versatile)<br/>3. OpenAI (GPT-4o)"]
    end

    subgraph Vector_Storage ["Vector Database (Qdrant)"]
        QdrantStore["Qdrant Cloud / Local Cluster<br/>• Tenant-Isolated Vector Collections<br/>• Payload Filtering by Microservice ID"]
    end

    UI_Dev -->|HTTP / SSE Streaming| API_Layer
    Auth --> DirectAdapter
    DirectAdapter --> RAG_Engine
    Chunker --> Embedder
    Embedder --> QdrantStore
    QdrantStore --> FallbackLLM
    FallbackLLM -->|Streamed Tokens| DirectAdapter
```

---

## 🚀 Key Technical Highlights

- **Multi-Provider LLM Resilience**: Dynamic multi-provider orchestration with automatic fallback between AWS Bedrock, Groq Cloud, and OpenAI to eliminate vendor lock-in and handle rate limits gracefully.
- **Tenant-Isolated Vector Storage**: Segmented retrieval pipelines utilizing Qdrant payload filters, guaranteeing strict isolation between microservice codebases and documentation collections.
- **Real-Time Token Streaming**: Server-Sent Events (SSE) streaming with ultra-low time-to-first-token (TTFT) and citation attribution.
- **AST & Header-Aware Chunking**: Specialized chunkers that respect code function boundaries and document section headers rather than splitting mid-token.
- **Clean Hexagonal Architecture**: Modular separation between Presentation, Application, Domain, and Infrastructure adapters following clean architecture principles.

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

## 🧪 Built-In Demo Login

For quick local evaluation, an engineer demo account is pre-configured:

| Role | Demo Email | Workspace | Description |
| :--- | :--- | :--- | :--- |
| **Software Engineer** | `engineer@contextfoundry.dev` | **Dev Central** | Explore architecture docs, ask RAG questions, and browse Knowledge Cafe courses. |

---

## 💼 Portfolio Highlights & Resume Summary

> **ContextFoundry — Autonomous Engineering Intelligence Platform for Microservices**
> - Architected a production-ready RAG platform serving software engineering teams navigating distributed microservice codebases.
> - Implemented an intelligent multi-provider LLM orchestration layer (AWS Bedrock, Groq, OpenAI) with automatic fallback and sub-second token streaming.
> - Designed tenant-isolated vector retrieval with Qdrant, supporting structured AST-aware chunking of source code, Markdown, and technical specifications.
> - Built a modern React 19 / TypeScript frontend featuring interactive courses, automated quizzes, live Markdown formatting, and automated Mermaid diagram rendering.
> - Containerized the entire multi-service stack using multi-stage Docker builds and Docker Compose for zero-friction local and cloud deployments.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

