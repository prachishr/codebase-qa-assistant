
# Codebase QA Assistant

An AI-powered codebase companion that helps developers understand GitHub repositories through natural-language questions. It uses Retrieval-Augmented Generation (RAG) to retrieve relevant code and documentation before generating repository-grounded answers.

**GitHub Repository:** [prachishr/codebase-qa-assistant](https://github.com/prachishr/codebase-qa-assistant)

---

## Overview

Codebase QA Assistant turns a GitHub repository into a searchable knowledge base. Users can connect a repository and ask questions about its purpose, implementation, architecture, functions, and documentation.

Instead of sending an entire repository to an LLM, the application:

1. Clones and processes the repository.
2. Extracts relevant source code and documentation.
3. Splits content into meaningful chunks.
4. Generates vector embeddings.
5. Retrieves relevant context using FAISS.
6. Sends the selected context to a Groq-hosted language model.
7. Returns answers based on the retrieved repository content.

The application also provides user authentication and PostgreSQL-backed conversation history, allowing users to revisit previous chats.

---

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/FAISS-Vector_Search-005571?style=for-the-badge" alt="FAISS">
  <img src="https://img.shields.io/badge/Groq-API-F55036?style=for-the-badge" alt="Groq">
  <img src="https://img.shields.io/badge/Neon-PostgreSQL-00E599?style=for-the-badge&logo=neon&logoColor=black" alt="Neon">
  <img src="https://img.shields.io/badge/Render-Deployment-46E3B7?style=for-the-badge&logo=render&logoColor=black" alt="Render">
</p>



## Features

- **User Authentication:** Sign-up and login through the FastAPI backend.
- **GitHub Repository Connection:** Clone and analyze supported public repositories.
- **Repository-Aware Question Answering:** Ask questions about the connected codebase.
- **Code and Documentation Ingestion:** Process source files and project documentation.
- **AST-Aware Code Chunking:** Identify meaningful code structures such as functions, methods, and classes where supported.
- **Semantic Search:** Generate embeddings using Sentence Transformers.
- **FAISS Vector Search:** Retrieve relevant repository chunks.
- **Hybrid Retrieval:** Combine keyword, code-symbol, project-overview, and semantic retrieval strategies.
- **Groq-Powered Responses:** Generate answers using retrieved repository context.
- **Source References:** Display relevant source files alongside answers.
- **Persistent Conversations:** Store chat history in PostgreSQL.
- **Previous Chats:** Reopen earlier conversations and view their associated repository.

---

## Architecture

The application follows a Retrieval-Augmented Generation (RAG) architecture to answer questions about GitHub repositories.

```mermaid
flowchart TD
    A[User] --> B[Frontend<br/>HTML, CSS, JavaScript]
    B --> C[FastAPI Backend]

    C --> D[Authentication]
    C --> E[Repository Management]
    C --> F[Conversation Management]

    E --> G[GitHub Repository]
    G --> H[Code and Documentation Ingestion]
    H --> I[AST-Aware Chunking]
    I --> J[Text Embeddings<br/>Sentence Transformers]
    J --> K[FAISS Vector Store]

    B --> L[User Question]
    L --> C
    C --> M[Retrieval Service]
    K --> M
    M --> N[Relevant Repository Context]
    N --> O[Groq LLM<br/>openai/gpt-oss-20b]
    O --> P[Generated Answer]
    P --> B

    D --> Q[(Neon PostgreSQL)]
    F --> Q
```

### RAG Workflow

1. The user connects a GitHub repository.
2. The backend clones and processes the repository.
3. Source code and documentation are divided into meaningful chunks.
4. Sentence Transformers generates vector embeddings.
5. FAISS stores the embeddings for similarity search.
6. The user submits a question through the frontend.
7. The retrieval service finds relevant repository content.
8. Retrieved context is passed to the Groq LLM.
9. The generated answer is returned to the frontend.
10. Conversation history is stored in Neon PostgreSQL.

### RAG Pipeline

**1. Repository Ingestion**

The application clones a supported public GitHub repository and extracts relevant source-code files and documentation.

**2. Chunking**

Code and documentation are processed according to their content:

- **Code:** AST-aware parsing identifies meaningful structures such as functions, methods, and classes for supported languages.
- **Documentation:** Markdown and text content are divided into smaller chunks.
- **Project Overview:** The root README receives particular importance for project-level questions.

**3. Embeddings**

Text chunks are converted into vector embeddings using:

`sentence-transformers/all-MiniLM-L6-v2`

The embedding model runs locally.

**4. Retrieval**

The retrieval layer uses strategies such as:

- Project-overview retrieval
- Keyword matching
- Code-symbol and function matching
- FAISS semantic similarity search
- Duplicate reduction
- Source prioritization

**5. Answer Generation**

Retrieved chunks are assembled into context and passed to the Groq language model.

**LLM:** `openai/gpt-oss-20b`

The model generates answers using the supplied repository context.

---

## Authentication and Conversation History

The FastAPI backend handles authentication and application APIs. PostgreSQL stores persistent application data, including conversation history.

The database layer uses SQLAlchemy's asynchronous interface with `asyncpg` to communicate with the PostgreSQL database hosted on Neon.

Conversation history is associated with the authenticated user. Conversations can also be associated with repositories, allowing users to identify which repository a previous chat belongs to.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | Backend API framework |
| HTML | Frontend structure |
| CSS | Frontend styling |
| JavaScript | Frontend interactions and API requests |
| SQLAlchemy (Async) | Asynchronous database operations |
| asyncpg | PostgreSQL driver |
| Neon PostgreSQL | Hosted relational database |
| GitPython | GitHub repository cloning and Git operations |
| Tree-sitter | AST-based code parsing |
| LangChain | Document and vector-store integration |
| Sentence Transformers | Local embedding generation |
| FAISS | Vector similarity search |
| Groq | LLM inference |
| python-dotenv | Environment variable configuration |

### Core AI Components

| Component | Model |
|---|---|
| Embedding Model | `sentence-transformers/all-MiniLM-L6-v2` |
| LLM | `openai/gpt-oss-20b` |

---

## Project Structure

```text
Codebase-QA-Assistant/
│
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/
│       │   └── v1/
│       │       ├── auth.py
│       │       ├── conversations.py
│       │       └── repositories.py
│       ├── core/
│       │   ├── config.py
│       │   ├── dependencies.py
│       │   └── security.py
│       ├── db/
│       │   ├── database.py
│       │   └── init_db.py
│       ├── models/
│       ├── schemas/
│       └── services/
│           ├── github_service.py
│           └── rag_service.py
│
├── core/
│   ├── chunking.py
│   ├── ingestion.py
│   ├── rag.py
│   ├── retrieval.py
│   ├── vector_store.py
│   └── __init__.py
│
├── frontend/
│   ├── index.html
│   ├── pages/
│   │   ├── login.html
│   │   ├── signup.html
│   │   └── dashboard.html
│   ├── css/
│   │   ├── style.css
│   │   ├── auth.css
│   │   └── dashboard.css
│   └── js/
│       ├── api.js
│       ├── auth.js
│       ├── dashboard.js
│       └── chat.js
│
├── workspaces/
├── requirements.txt
├── .gitignore
├── .env
└── README.md
```

Generated repository files and vector indexes are created locally as needed and excluded from Git.

---

## Local Setup
Follow these steps to run Codebase QA Assistant on your local machine
### Prerequisites

Before running the project, make sure you have:

- Python installed
- Git installed
- A Groq API key
- A PostgreSQL database (the project uses Neon)

### 1. Clone the Repository

```bash
git clone https://github.com/prachishr/codebase-qa-assistant.git
cd codebase-qa-assistant
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables

Create a `.env` file in the root directory of the project.

Add the following environment variables:

```env
APP_NAME="Codebase QA Assistant API"
APP_ENV=development

DATABASE_URL=your_neon_postgresql_connection_string
GROQ_API_KEY=your_groq_api_key
JWT_SECRET_KEY=your_secure_jwt_secret

FRONTEND_URL=http://localhost:5173
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Replace the placeholder values with your actual credentials.

| Variable | Description |
|---|---|
| `APP_NAME` | Application name |
| `APP_ENV` | Application environment |
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `GROQ_API_KEY` | API key used for Groq |
| `JWT_SECRET_KEY` | Secret key used for JWT authentication |
| `FRONTEND_URL` | Frontend application URL |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiration time in minutes |

**Important:** Never commit your `.env` file to GitHub or expose your API keys, database credentials, or JWT secret.

### 6. Run the FastAPI Backend

From the project root, execute:

```bash
python -m uvicorn backend.app.main:app --reload
```

The backend will be available at:

`http://127.0.0.1:8000`

### 7. Access API Documentation

FastAPI provides interactive API documentation at:

`http://127.0.0.1:8000/docs`

Health endpoint:

`http://127.0.0.1:8000/health`

### 8. Open the Frontend

Open `frontend/index.html` using a local static server, such as the VS Code Live Server extension.

Make sure the frontend API configuration points to the running FastAPI backend.

---

## Example Questions

After connecting a repository, users can ask:

- What is this project about?
- Explain the project architecture.
- How does the `loadRules` function work?
- Which file handles authentication?
- Where is the database connection created?
- What are the main technologies used in this repository?
- Explain the flow of data through this application.

---

## Why These Technologies?

| Technology | Reason |
|---|---|
| RAG | Grounds LLM responses in retrieved repository content |
| FastAPI | Provides a structured backend API |
| HTML, CSS, and JavaScript | Provides a separate frontend |
| Tree-sitter | Helps identify meaningful code structures |
| MiniLM Embeddings | Generates lightweight semantic representations |
| FAISS | Enables local vector similarity search |
| Groq | Provides LLM inference |
| PostgreSQL | Stores persistent relational application data |
| Neon | Hosts the PostgreSQL database |

### Why FAISS Instead of ChromaDB?

ChromaDB was initially explored for vector storage, but the Windows environment encountered a `cygrpc` DLL loading issue related to an Application Control policy.

FAISS provided the required local vector similarity search without the problematic gRPC dependency, so the project moved to FAISS.

---

## Current Limitations

- The application currently supports public GitHub repositories.
- Repository cloning uses a shallow clone, so the full Git history is not available.
- Very large repositories may require additional processing time.
- Repository workspaces and FAISS indexes are stored in the application's local workspace.
- Local or ephemeral deployment storage may require repository re-ingestion and index regeneration after a restart or redeployment.
- Private repository access is not currently provided through a GitHub OAuth integration.

---

## Future Improvements

- GitHub OAuth and private repository support
- Full Git history analysis
- Support for additional programming languages
- Improved retrieval and reranking
- Repository dependency visualization
- Streaming LLM responses
- Background repository indexing
- Persistent vector-index storage
- Improved code and source highlighting
- Repository-aware code generation

---

## Project Highlights

Generative AI · Large Language Models · Retrieval-Augmented Generation · Semantic Search · Vector Embeddings · FAISS · AST Parsing · Code Intelligence · GitHub Integration · FastAPI · JavaScript · PostgreSQL · Authentication

---

## Author

**Prachi Sharma**

GitHub: [prachishr](https://github.com/prachishr)

Project Repository: [codebase-qa-assistant](https://github.com/prachishr/codebase-qa-assistant)

If you find this project useful, consider giving the repository a ⭐ on GitHub.
