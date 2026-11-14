from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import re


FAISS_PATH = "faiss_index"


def load_vector_store():

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = FAISS.load_local(
        FAISS_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return vector_store


def get_project_overview(vector_store):

    for doc_id in vector_store.index_to_docstore_id.values():

        document = vector_store.docstore.search(doc_id)

        if document is None:
            continue

        if document.metadata.get("section") == "project_overview":
            return [document]

    return []


def keyword_search(vector_store, question, k=5):

    question_lower = question.lower()

    keywords = []

    keyword_map = {
        "install": [
            "install",
            "installation",
            "setup",
            "requirements"
        ],

        "how": [
            "workflow",
            "architecture",
            "implementation",
            "process"
        ],

        "code": [
            "code",
            "function",
            "class",
            "implementation"
        ],

        "documentation": [
            "documentation",
            "docs",
            "readme"
        ]
    }

    for category_keywords in keyword_map.values():

        for keyword in category_keywords:

            if keyword in question_lower:
                keywords.append(keyword)

    matching_documents = []

    for doc_id in vector_store.index_to_docstore_id.values():

        document = vector_store.docstore.search(doc_id)

        if document is None:
            continue

        file_name = document.metadata.get(
            "file",
            ""
        ).lower()

        content = document.page_content.lower()

        score = 0

        for keyword in keywords:

            if keyword in file_name:
                score += 5

            if keyword in content:
                score += 1

        if score > 0:

            matching_documents.append(
                (score, document)
            )

    matching_documents.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        document
        for score, document in matching_documents[:k]
    ]


def search_repository(question, k=5):

    vector_store = load_vector_store()

    question_lower = question.lower()

    # --------------------------------------------------
    # Exact function / class name search
    # --------------------------------------------------

    code_documents = []

    for doc_id in vector_store.index_to_docstore_id.values():

        document = vector_store.docstore.search(doc_id)

        if document is None:
            continue

        if document.metadata.get("type") == "code":
            code_documents.append(document)

    # Extract possible code symbol names from the question
    for document in code_documents:

        content = document.page_content

        function_names = re.findall(
            r"(?:function\s+|def\s+|class\s+|)\b([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            content
        )

        for function_name in function_names:

            if function_name.lower() in question_lower:

                return [document]

    # --------------------------------------------------
    # Exact code symbol search
    # --------------------------------------------------

    symbol_match = re.search(
        r"\b(?:function|method|class)?\s*([A-Za-z_][A-Za-z0-9_]*)\b",
        question_lower
    )

    if symbol_match:

        symbol_name = symbol_match.group(1)

        exact_matches = []

        for doc_id in vector_store.index_to_docstore_id.values():

            document = vector_store.docstore.search(doc_id)

            if document is None:
                continue

            if document.metadata.get("type") != "code":
                continue

            content_lower = document.page_content.lower()

            pattern = rf"\b{re.escape(symbol_name)}\s*\("

            if re.search(pattern, content_lower):

                exact_matches.append(document)

        if exact_matches:

            return exact_matches[:k]

    # --------------------------------------------------
    # Project overview questions
    # --------------------------------------------------

    overview_keywords = [
        "what is this project",
        "what does this project",
        "what is the project",
        "project about",
        "about this project",
        "purpose of this project",
        "what does this repository",
        "what is this repository"
    ]

    is_overview_question = any(
        keyword in question_lower
        for keyword in overview_keywords
    )

    if is_overview_question:

        overview = get_project_overview(
            vector_store
        )

        if overview:
            return overview

    # --------------------------------------------------
    # Keyword-based retrieval
    # --------------------------------------------------

    keyword_results = keyword_search(
        vector_store,
        question,
        k=k
    )

    # --------------------------------------------------
    # Semantic retrieval
    # --------------------------------------------------

    semantic_results = vector_store.similarity_search(
        question,
        k=k * 2
    )

    # --------------------------------------------------
    # Prefer code for implementation questions
    # --------------------------------------------------

    technical_keywords = [
        "how does",
        "how is",
        "where is",
        "which function",
        "which class",
        "implemented",
        "implementation",
        "code",
        "function",
        "class",
        "logic"
    ]

    is_technical_question = any(
        keyword in question_lower
        for keyword in technical_keywords
    )

    if is_technical_question:

        code_results = [
            document
            for document in semantic_results
            if document.metadata.get("type") == "code"
        ]

        semantic_results = (
            code_results +
            [
                document
                for document in semantic_results
                if document.metadata.get("type") != "code"
            ]
        )

    # --------------------------------------------------
    # Combine results
    # --------------------------------------------------
    combined = []

    seen_chunks = set()
    file_counts = {}

    for document in keyword_results + semantic_results:

        content = document.page_content
        file_name = document.metadata.get("file", "Unknown")

        # Avoid exact duplicate chunks
        chunk_id = (
            file_name,
            content
        )

        if chunk_id in seen_chunks:
            continue

        # Avoid returning too many chunks from the same file
        if file_counts.get(file_name, 0) >= 2:
            continue

        combined.append(document)

        seen_chunks.add(chunk_id)

        file_counts[file_name] = (
            file_counts.get(file_name, 0) + 1
        )

    return combined[:k]


if __name__ == "__main__":

    question = input(
        "\nAsk a question about the repository: "
    )

    results = search_repository(question)

    print("\nSearch Results")
    print("----------------")

    for i, result in enumerate(
        results,
        start=1
    ):

        print(f"\nResult {i}:")

        print(
            "Type:",
            result.metadata.get("type")
        )

        print(
            "File:",
            result.metadata.get("file")
        )

        print(
            "Path:",
            result.metadata.get("path")
        )

        print(
            "Section:",
            result.metadata.get("section")
        )

        print("\nContent:")
        print(result.page_content)

        print("-" * 60)