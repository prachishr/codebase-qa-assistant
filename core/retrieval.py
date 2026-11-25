
"""Repository retrieval using FAISS, semantic search, and keyword ranking."""

import re
import os
import threading
from pathlib import Path
from functools import lru_cache

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS


FAISS_PATH = "faiss_index"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_VECTOR_STORE_CACHE = {}
_VECTOR_STORE_LOCK = threading.Lock()


class LocalONNXEmbeddings(Embeddings):
    """Local CPU embeddings using ONNX Runtime and HuggingFace tokenizers."""

    def __init__(
        self,
        model_id: str = DEFAULT_EMBEDDING_MODEL,
        max_length: int = 256,
        batch_size: int = 32,
    ):
        self.model_id = model_id
        self.max_length = max_length
        self.batch_size = batch_size

        tokenizer_path = self._get_model_file("tokenizer.json")
        model_path = self._get_model_file("onnx/model.onnx")

        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_truncation(max_length=self.max_length)
        pad_id = self._tokenizer.token_to_id("[PAD]")
        self._tokenizer.enable_padding(
            pad_id=pad_id if pad_id is not None else 0,
            pad_token="[PAD]",
        )

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        self._session = ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )
        self._input_names = {inp.name for inp in self._session.get_inputs()}

    def _get_model_file(self, filename: str) -> str:
        """Use cached HuggingFace file without network calls when available."""
        try:
            return hf_hub_download(
                repo_id=self.model_id,
                filename=filename,
                local_files_only=True,
            )
        except Exception:
            return hf_hub_download(
                repo_id=self.model_id,
                filename=filename,
            )

    def _encode_batch(self, texts: list[str]) -> np.ndarray:
        encodings = self._tokenizer.encode_batch(texts)
        input_ids = np.array([enc.ids for enc in encodings], dtype=np.int64)
        attention_mask = np.array(
            [enc.attention_mask for enc in encodings],
            dtype=np.int64,
        )

        feed_dict = {}
        if "input_ids" in self._input_names:
            feed_dict["input_ids"] = input_ids
        if "attention_mask" in self._input_names:
            feed_dict["attention_mask"] = attention_mask
        if "token_type_ids" in self._input_names:
            feed_dict["token_type_ids"] = np.array(
                [enc.type_ids for enc in encodings],
                dtype=np.int64,
            )

        token_embeddings = self._session.run(None, feed_dict)[0]

        mask = attention_mask[..., None].astype(np.float32)
        summed = np.sum(token_embeddings * mask, axis=1)
        counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
        pooled = summed / counts

        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        normalized = pooled / np.clip(norms, a_min=1e-12, a_max=None)
        return normalized

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            vectors = self._encode_batch(batch)
            results.extend(vectors.tolist())
        return results

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


# --------------------------------------------------
# Load and reuse embedding model
# --------------------------------------------------

@lru_cache(maxsize=1)
def get_embeddings():
    """Load and reuse local ONNX embeddings (no API key or daily limit)."""
    model_id = os.getenv("EMBEDDING_MODEL_ID", DEFAULT_EMBEDDING_MODEL)
    return LocalONNXEmbeddings(model_id=model_id)


def invalidate_vector_store_cache(index_path=None):
    """Clear cached FAISS vector store(s) after re-indexing or deletion."""
    with _VECTOR_STORE_LOCK:
        if index_path is None:
            _VECTOR_STORE_CACHE.clear()
        else:
            key = str(Path(index_path).resolve())
            _VECTOR_STORE_CACHE.pop(key, None)


# --------------------------------------------------
# Load FAISS vector store
# --------------------------------------------------

def load_vector_store(index_path=FAISS_PATH):

    resolved_path = Path(index_path).resolve()
    faiss_file = resolved_path / "index.faiss"
    pkl_file = resolved_path / "index.pkl"

    if not faiss_file.exists() or not pkl_file.exists():
        raise FileNotFoundError(
            "FAISS index is missing or incomplete. Please index or re-index the repository."
        )

    mtime = (faiss_file.stat().st_mtime, pkl_file.stat().st_mtime)
    cache_key = str(resolved_path)

    with _VECTOR_STORE_LOCK:
        cached = _VECTOR_STORE_CACHE.get(cache_key)
        if cached and cached[0] == mtime:
            return cached[1]

    embeddings = get_embeddings()

    vector_store = FAISS.load_local(
        str(resolved_path),
        embeddings,
        allow_dangerous_deserialization=True
    )

    with _VECTOR_STORE_LOCK:
        _VECTOR_STORE_CACHE[cache_key] = (mtime, vector_store)

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
            "similarity search", "onnx"
        ],
        "files": ["vector_store.py", "retrieval.py"],
        "keywords": [
            "LocalONNXEmbeddings",
            "InferenceSession",
            "all-MiniLM-L6-v2",
            "FAISS",
            "from_embeddings",
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

    word_patterns = [
        (word, re.compile(r"\b" + re.escape(word) + r"\b"))
        for word in searchable_words
    ]

    for doc_id in vector_store.index_to_docstore_id.values():

        document = vector_store.docstore.search(doc_id)

        if document is None:
            continue

        file_name = document.metadata.get("file", "").lower()
        content = document.page_content.lower()
        score = 0

        for word, pattern in word_patterns:

            if word in file_name:
                score += 5

            if pattern.search(content):
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

    query_vector = vector_store.embedding_function.embed_query(question)
    index_dim = getattr(vector_store.index, "d", None)
    if index_dim is not None and len(query_vector) != index_dim:
        raise ValueError(
            f"FAISS index dimension mismatch (index has {index_dim}, "
            f"embedding model produces {len(query_vector)}). "
            "Please click Re-index to rebuild this repository's FAISS index."
        )

    semantic_results = vector_store.similarity_search_by_vector(
        query_vector,
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
