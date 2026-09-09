# 💻 Codebase QA Assistant

An AI-powered repository assistant that analyzes GitHub codebases and answers questions about their source code, documentation, and project structure using Retrieval-Augmented Generation (RAG).

## 🚀 Live Demo
[
[Open the deployed application](https://prachishr-codebase-qa-assistant-app-pfv58a.streamlit.app/)
]
---

## 📌 Overview

Codebase QA Assistant allows users to provide a public GitHub repository URL and ask natural-language questions about the repository.

The application:

1. Clones the GitHub repository
2. Extracts source code and documentation
3. Extracts available Git history
4. Creates AST-aware chunks for source code
5. Splits documentation into meaningful text chunks
6. Generates vector embeddings using Hugging Face
7. Stores embeddings in a FAISS vector database
8. Retrieves relevant repository content
9. Uses a Groq-hosted LLM to generate grounded answers
10. Displays relevant source files with each answer

The goal is to provide a **ChatGPT-like interface for understanding software repositories**.

---

## ✨ Features

- 🔗 Analyze public GitHub repositories
- 📄 Extract source code and documentation
- 🌳 AST-aware code chunking
- 🧠 Local Hugging Face embeddings
- 🔎 FAISS vector similarity search
- 🎯 Keyword-based retrieval
- 🔍 Exact function/symbol retrieval
- 🤖 Retrieval-Augmented Generation (RAG)
- ⚡ Groq-powered LLM responses
- 📚 Source file attribution
- 💬 Interactive Streamlit chat interface
- 🔐 API key stored securely using environment variables

---

## 🏗️ Architecture

```text
                GitHub Repository
                       │
                       ▼
                Repository Clone
                       │
                       ▼
              ┌─────────────────┐
              │    Ingestion    │
              │ Code + Docs +   │
              │   Git History   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    Chunking     │
              │                 │
              │ AST-aware Code  │
              │ Documentation   │
              │ Text Splitting  │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Embeddings    │
              │ Hugging Face    │
              │ MiniLM Model    │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │      FAISS      │
              │ Vector Database │
              └────────┬────────┘
                       │
             User Question
                       │
                       ▼
              ┌─────────────────┐
              │    Retrieval    │
              │ Semantic +      │
              │ Keyword +       │
              │ Symbol Search   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    Groq LLM     │
              │  RAG Generation │
              └────────┬────────┘
                       │
                       ▼
                Answer + Sources


#### Author
Prachi Sharma
