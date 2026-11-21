
"""Create and save FAISS vector stores using cached embeddings."""

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .retrieval import get_embeddings


def create_vector_store(chunks, index_path="faiss_index"):

    if not chunks:
        raise ValueError(
            "No chunks provided. Cannot create vector store."
        )

    print(f"Chunks received: {len(chunks)}")

    # Reuse the cached embedding model
    print("\nLoading embedding model...")

    embeddings = get_embeddings()

    # Convert chunks into LangChain Documents
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

    # Create FAISS vector store
    print("Creating FAISS vector database...")

    vector_store = FAISS.from_documents(
        documents=langchain_documents,
        embedding=embeddings
    )

    # Save vector store locally
    vector_store.save_local(index_path)

    print("\nVector database created successfully!")
    print(f"Saved to: {index_path}/")

    return vector_store
