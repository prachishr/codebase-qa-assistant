
"""Repository retrieval using FAISS, semantic search, and keyword ranking."""

import re
import os
from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS


FAISS_PATH = "faiss_index"


# --------------------------------------------------
# Load and reuse embedding model
# --------------------------------------------------

@lru_cache(maxsize=1)
def get_embeddings():
    """Load and reuse Gemini embeddings."""

    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.environ["GEMINI_API_KEY"]
    )


# --------------------------------------------------
# Load FAISS vector store
# --------------------------------------------------

def load_vector_store(index_path=FAISS_PATH):

    embeddings = get_embeddings()

    vector_store = FAISS.load_local(
        index_path,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return vector_store


# --------------------------------------------------
# Project overview retrieval
# --------------------------------------------------

def get_project_overview(vector_store, k=5):

    overview_documents = []
    seen_documents = set()

    for doc_id in vector_store.index_to_docstore_id.values():

        document = vector_store.docstore.search(doc_id)

        if document is None:
            continue

        if document.metadata.get("section") != "project_overview":
            continue

        file_name = document.metadata.get("file", "")
        content = document.page_content.strip()

        document_key = (file_name, content)

        if document_key in seen_documents:
            continue

        seen_documents.add(document_key)
        overview_documents.append(document)

        if len(overview_documents) >= k:
            break

    return overview_documents


# --------------------------------------------------
# Query intent and topic mapping
# --------------------------------------------------

TOPIC_MAP = {

    "ingestion": {
        "triggers": [
            "ingestion", "ingest", "document ingestion",
            "data ingestion", "extract", "load repository",
            "repository loading", "read repository",
            "git history", "load documents", "extract documents",
            "repository files", "sensitive files", "sensitive file",
            "large files", "large file", "file size", "size limit",
            "ignored files", "ignored directories", "excluded files",
            "file filtering", "file protection", "secret files",
            "credentials", "private keys"
        ],
        "files": ["ingestion.py"],
        "keywords": [
            "load_repository", "extract_code",
            "extract_documentation", "extract_git_history",
            "MAX_FILE_SIZE", "os.walk", "sensitive_files"
        ]
    },

    "chunking": {
        "triggers": [
            "chunk", "chunks", "chunking",
            "split documents", "text splitter", "ast"
        ],
        "files": ["chunking.py"],
        "keywords": [
            "create_chunks", "get_code_chunks",
            "chunk_size", "chunk_overlap",
            "RecursiveCharacterTextSplitter", "tree-sitter"
        ]
    },

    "embeddings": {
        "triggers": [
            "embedding", "embeddings", "embed", "vector",
            "vector database", "vector store", "faiss",
            "similarity search"
        ],
        "files": ["vector_store.py", "retrieval.py"],
        "keywords": [
            "GoogleGenerativeAIEmbeddings",
            "gemini-embedding-001",
            "GEMINI_API_KEY",
            "FAISS",
            "from_documents",
            "save_local",
            "load_local"
        ]
    },

    "retrieval": {
        "triggers": [
            "retrieval", "retrieve", "search", "similarity",
            "relevant documents", "relevant chunks", "keyword search"
        ],
        "files": ["retrieval.py"],
        "keywords": [
            "search_repository", "keyword_search",
            "similarity_search", "get_project_overview"
        ]
    },

    "rag": {
        "triggers": [
            "rag", "generation", "generate answer", "llm",
            "groq", "language model"
        ],
        "files": ["rag.py"],
        "keywords": [
            "generate_answer", "Groq",
            "chat.completions.create", "MODEL_NAME", "system_prompt"
        ]
    },

    "authentication": {
        "triggers": [
            "authentication", "auth", "login", "signup",
            "sign up", "password", "jwt", "token"
        ],
        "files": [
            "security.py", "auth.py", "dependencies.py"
        ],
        "keywords": [
            "hash_password", "verify_password",
            "create_access_token", "jwt.encode", "jwt.decode"
        ]
    },

    "database": {
        "triggers": [
            "database", "postgresql", "postgres", "sqlalchemy",
            "database connection", "database tables"
        ],
        "files": [
            "database.py", "user.py", "repository.py",
            "conversation.py", "message.py"
        ],
        "keywords": [
            "create_async_engine", "AsyncSession",
            "DeclarativeBase", "ForeignKey", "mapped_column"
        ]
    }
}


# --------------------------------------------------
# Detect relevant topics
# --------------------------------------------------

def detect_topics(question):

    question_lower = question.lower()
    detected_topics = []

    for topic, details in TOPIC_MAP.items():

        if any(
            trigger in question_lower
            for trigger in details["triggers"]
        ):
            detected_topics.append(topic)

    return detected_topics


# --------------------------------------------------
# Explicit function / class name search
# --------------------------------------------------

def extract_explicit_symbols(question):

    symbols = set()

    symbols.update(
        re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", question)
    )

    patterns = [
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bmethod\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            question,
            re.IGNORECASE
        )

        symbols.update(matches)

    return symbols


def find_symbol_documents(vector_store, symbols, k=5):

    if not symbols:
        return []

    matching_documents = []

    definition_pattern = re.compile(
        r"^\s*(?:async\s+)?"
        r"(?:def|class|function)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",
        re.MULTILINE
    )

    for doc_id in vector_store.index_to_docstore_id.values():

        document = vector_store.docstore.search(doc_id)

        if document is None:
            continue

        definitions = definition_pattern.findall(
            document.page_content
        )

        if any(
            symbol in definitions
            for symbol in symbols
        ):
            matching_documents.append(document)

    return matching_documents[:k]


# --------------------------------------------------
# Keyword-based retrieval
# --------------------------------------------------

def keyword_search(
    vector_store,
    question,
    k=5,
    topics=None
):
    """Find chunks using exact question terms and topic-specific identifiers."""

    question_lower = question.lower()
    topics = topics or []
    matching_documents = []

    question_words = set(
        re.findall(
            r"[a-zA-Z_][a-zA-Z0-9_]*",
            question_lower
        )
    )

    ignored_words = {
        "what", "which", "where", "when", "why", "does", "this",
        "that", "these", "those", "the", "how", "are", "is", "and",
        "into", "from", "with", "for", "can", "will", "would",
        "should", "could", "about", "explain", "describe", "tell",
        "show", "give", "please", "using", "used", "include",
        "including", "relevant", "actual", "exact", "implementation",
        "implemented", "functionality", "function", "files", "file"
    }

    searchable_words = {
        word for word in question_words
        if word not in ignored_words and len(word) >= 3
    }

    for doc_id in vector_store.index_to_docstore_id.values():

        document = vector_store.docstore.search(doc_id)

        if document is None:
            continue

        file_name = document.metadata.get("file", "").lower()
        content = document.page_content.lower()
        score = 0

        for word in searchable_words:

            if word in file_name:
                score += 5

            if re.search(
                r"\b" + re.escape(word) + r"\b",
                content
            ):
                score += 3

        for topic in topics:

            topic_details = TOPIC_MAP[topic]

            if any(
                name.lower() in file_name
                for name in topic_details["files"]
            ):
                score += 15

            for keyword in topic_details["keywords"]:

                if keyword.lower() in content:
                    score += 8

        if score > 0:
            matching_documents.append((score, document))

    matching_documents.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        document
        for score, document in matching_documents[:k * 5]
    ]


# --------------------------------------------------
# Technical question detection
# --------------------------------------------------

def is_technical_question(question):

    technical_keywords = [
        "how", "implemented", "implementation",
        "function", "class", "code", "workflow",
        "process", "architecture", "logic", "work",
        "stored", "created", "generated"
    ]

    question_lower = question.lower()

    return any(
        keyword in question_lower
        for keyword in technical_keywords
    )


# --------------------------------------------------
# Main repository retrieval
# --------------------------------------------------

def search_repository(
    question,
    k=5,
    index_path=FAISS_PATH
):

    vector_store = load_vector_store(index_path)

    question_lower = question.lower()

    # 1. Project overview questions

    overview_keywords = [
        "what is this project",
        "what does this project",
        "what is the project",
        "project about",
        "about this project",
        "purpose of this project",
        "what does this repository",
        "what is this repository",
        "overall repository structure",
        "repository structure",
        "project structure",
        "overall project structure",
        "main components",
        "project architecture",
        "repository architecture",
        "overall architecture",
        "repository layout",
        "project layout"
    ]

    is_overview_question = any(
        keyword in question_lower
        for keyword in overview_keywords
    )

    if is_overview_question:

        overview = get_project_overview(vector_store)

        if overview:
            return overview

    # 2. Explicit function / class search

    symbols = extract_explicit_symbols(question)

    if symbols:

        symbol_results = find_symbol_documents(
            vector_store,
            symbols,
            k=k
        )

        if symbol_results:
            return symbol_results

    # 3. Detect relevant topics

    topics = detect_topics(question)

    # 4. Keyword retrieval

    keyword_results = keyword_search(
        vector_store,
        question,
        k=k,
        topics=topics
    )

    # 5. Semantic retrieval

    semantic_results = vector_store.similarity_search(
        question,
        k=k * 3
    )

    # 6. Combine and rank documents

    document_scores = {}

    for document in keyword_results:

        key = (
            document.metadata.get("file", ""),
            document.page_content
        )

        document_scores[key] = {
            "document": document,
            "score": 10
        }

    for rank, document in enumerate(semantic_results):

        key = (
            document.metadata.get("file", ""),
            document.page_content
        )

        semantic_score = max(1, 8 - rank)

        if key in document_scores:

            document_scores[key]["score"] += semantic_score

        else:

            document_scores[key] = {
                "document": document,
                "score": semantic_score
            }

    # 7. Apply topic-based relevance boosts

    for item in document_scores.values():

        document = item["document"]

        file_name = document.metadata.get(
            "file",
            ""
        ).lower()

        content = document.page_content.lower()

        for topic in topics:

            topic_details = TOPIC_MAP[topic]

            if any(
                name.lower() in file_name
                for name in topic_details["files"]
            ):
                item["score"] += 15

            for keyword in topic_details["keywords"]:

                if keyword.lower() in content:
                    item["score"] += 3

    # 8. Sort by relevance

    ranked_documents = sorted(
        document_scores.values(),
        key=lambda item: item["score"],
        reverse=True
    )

    # 9. Select relevant documents

    selected_documents = []
    file_counts = {}

    max_chunks_per_file = (
        k if len(topics) == 1 else 2
    )

    for item in ranked_documents:

        document = item["document"]

        file_name = document.metadata.get(
            "file",
            "Unknown"
        )

        if file_counts.get(file_name, 0) >= max_chunks_per_file:
            continue

        selected_documents.append(document)

        file_counts[file_name] = (
            file_counts.get(file_name, 0) + 1
        )

        if len(selected_documents) >= k:
            break

    return selected_documents


# --------------------------------------------------
# Local testing
# --------------------------------------------------

if __name__ == "__main__":

    question = input(
        "\nAsk a question about the repository: "
    )

    results = search_repository(question)

    print("\nSearch Results")
    print("----------------")

    for i, result in enumerate(results, start=1):

        print(f"\nResult {i}")
        print("File:", result.metadata.get("file"))
        print("Type:", result.metadata.get("type"))
        print("Section:", result.metadata.get("section"))

        print("\nContent:")
        print(result.page_content)

        print("-" * 60)
