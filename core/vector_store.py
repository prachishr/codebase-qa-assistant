
"""Create and save FAISS vector stores using rate-controlled Gemini embeddings."""

import time

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .retrieval import get_embeddings


BATCH_SIZE = 40
BATCH_DELAY = 35
MAX_RETRIES = 3


def embed_with_retry(embeddings, texts, batch_number):
    """Embed one batch, retrying temporary Gemini quota errors."""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(
                f"Embedding batch {batch_number} "
                f"({len(texts)} documents)..."
            )

            return embeddings.embed_documents(texts)

        except Exception as error:
            error_message = str(error).upper()

            is_rate_limit = (
                "429" in error_message
                or "RESOURCE_EXHAUSTED" in error_message
            )

            if not is_rate_limit or attempt == MAX_RETRIES:
                raise

            wait_time = 35 * attempt

            print(
                f"Gemini rate limit reached. "
                f"Retrying in {wait_time} seconds "
                f"(attempt {attempt}/{MAX_RETRIES})..."
            )

            time.sleep(wait_time)


def create_vector_store(chunks, index_path="faiss_index"):

    if not chunks:
        raise ValueError(
            "No chunks provided. Cannot create vector store."
        )

    print(f"Chunks received: {len(chunks)}")

    print("\nLoading Gemini embeddings...")
    embeddings = get_embeddings()

    print("Preparing documents...")

    langchain_documents = []

    for chunk in chunks:
        document = Document(
            page_content=chunk["content"],
            metadata={
                "type": chunk["type"],
                "file": chunk["file"],
                "path": chunk["path"],
                "source_priority": chunk.get(
                    "source_priority",
                    "normal"
                ),
                "section": chunk.get(
                    "section",
                    "general"
                )
            }
        )

        langchain_documents.append(document)

    texts = [
        document.page_content
        for document in langchain_documents
    ]

    metadatas = [
        document.metadata
        for document in langchain_documents
    ]

    print("\nCreating embeddings in controlled batches...")

    text_embeddings = []

    total_batches = (
        len(texts) + BATCH_SIZE - 1
    ) // BATCH_SIZE

    for batch_index, start in enumerate(
        range(0, len(texts), BATCH_SIZE),
        start=1
    ):

        batch_texts = texts[start:start + BATCH_SIZE]

        batch_embeddings = embed_with_retry(
            embeddings,
            batch_texts,
            batch_index
        )

        if len(batch_embeddings) != len(batch_texts):
            raise ValueError(
                "Gemini returned an unexpected number of embeddings."
            )

        text_embeddings.extend(
            zip(batch_texts, batch_embeddings)
        )

        print(
            f"Completed batch {batch_index}/{total_batches}"
        )

        if batch_index < total_batches:
            print(
                f"Waiting {BATCH_DELAY} seconds "
                "before the next batch..."
            )
            time.sleep(BATCH_DELAY)

    print("\nCreating FAISS vector database...")

    vector_store = FAISS.from_embeddings(
        text_embeddings=text_embeddings,
        embedding=embeddings,
        metadatas=metadatas
    )

    print("\nSaving FAISS vector database...")

    vector_store.save_local(index_path)

    print("\nVector database created successfully!")
    print(f"Saved to: {index_path}/")

    return vector_store
