
"""Create and save FAISS vector stores using local ONNX embeddings."""

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .retrieval import get_embeddings, invalidate_vector_store_cache


BATCH_SIZE = 32


def create_vector_store(chunks, index_path="faiss_index", progress_callback=None):

    valid_chunks = [
        chunk for chunk in (chunks or [])
        if chunk.get("content") and chunk["content"].strip()
    ]

    if not valid_chunks:
        raise ValueError(
            "No non-empty chunks provided. Cannot create vector store."
        )

    print(f"Chunks received: {len(valid_chunks)}")

    print("\nLoading local ONNX embeddings...")
    embeddings = get_embeddings()

    print("Preparing documents...")

    langchain_documents = []

    for chunk in valid_chunks:
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

    print("\nCreating embeddings locally via ONNX Runtime...")

    text_embeddings = []

    total_batches = (
        len(texts) + BATCH_SIZE - 1
    ) // BATCH_SIZE

    for batch_index, start in enumerate(
        range(0, len(texts), BATCH_SIZE),
        start=1
    ):

        batch_texts = texts[start:start + BATCH_SIZE]

        batch_embeddings = embeddings.embed_documents(batch_texts)

        if len(batch_embeddings) != len(batch_texts):
            raise ValueError(
                "Embedding model returned an unexpected number of embeddings."
            )

        text_embeddings.extend(
            zip(batch_texts, batch_embeddings)
        )

        print(
            f"Completed batch {batch_index}/{total_batches}"
        )

        if progress_callback is not None:
            progress_callback(batch_index, total_batches, len(text_embeddings), len(texts))

    print("\nCreating FAISS vector database...")

    vector_store = FAISS.from_embeddings(
        text_embeddings=text_embeddings,
        embedding=embeddings,
        metadatas=metadatas
    )

    print("\nSaving FAISS vector database...")

    vector_store.save_local(index_path)
    invalidate_vector_store_cache(index_path)

    print("\nVector database created successfully!")
    print(f"Saved to: {index_path}/")

    return vector_store
