#  Codebase QA Assistant

An AI-powered tool that lets users connect a GitHub repository and ask questions about its code, documentation, project structure, and Git information.

The application uses **Retrieval-Augmented Generation (RAG)** to retrieve relevant repository content before generating answers with an LLM.

## 🚀 Live Demo

**Streamlit App:** [Live App](https://prachishr-codebase-qa-assistant-app-pfv58a.streamlit.app/)

**GitHub:** [prachishr/codebase-qa-assistant](https://github.com/prachishr/codebase-qa-assistant)

---

## ✨ Features

- 🔐 **User Authentication** using Supabase Auth
- 💬 **Private Conversation History** using PostgreSQL
- 🐙 **GitHub Repository Analysis**
- 🧩 **AST-aware Code Chunking**
- 📚 **Documentation Processing**
- 🔎 **Semantic & Keyword-based Retrieval**
- 🤗 **Local Hugging Face Embeddings**
- ⚡ **FAISS Vector Search**
- 🤖 **Groq LLM-powered Answers**
- 📄 **Source File References**
- ☁️ **Streamlit Cloud Deployment**

---

## 🏗️ How It Works

```text
User
 ↓
Supabase Authentication
 ↓
GitHub Repository URL
 ↓
Repository Ingestion
 ├── Source Code
 ├── Documentation
 └── Git Information
 ↓
AST-aware / Text Chunking
 ↓
Hugging Face Embeddings
 ↓
FAISS Vector Search
 ↓
User Question
 ↓
Retrieve Relevant Repository Chunks
 ↓
Groq LLM
 ↓
Grounded Answer + Source Files

          ↘
            PostgreSQL
          Conversation History
```
# 📂 Project Structure
```
Codebase-QA-Assistant/
│
├── app.py
├── ingestion.py
├── chunking.py
├── vector_store.py
├── retrieval.py
├── RAG.py
├── database.py
│
├── requirements.txt
├── README.md
├── .gitignore
│
└── .env
```

### 👩‍💻 Author

Prachi Sharma

Github: [prachishr/codebase-qa-assistant](https://github.com/prachishr/codebase-qa-assistant)
