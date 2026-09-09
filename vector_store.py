from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from ingestion import load_repository
from chunking import create_chunks


REPO_PATH = "repo"


def create_vector_store():

    # Load repository documents
    documents = load_repository(REPO_PATH)

    # Create chunks
    chunks = create_chunks(documents)

    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")

    # Create embedding model
    print("\nLoading embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Convert our chunks into LangChain Documents
    langchain_documents = []

    for chunk in chunks:

        document = Document(
            page_content=chunk["content"],
            metadata={
                "type": chunk["type"],
                "file": chunk["file"],
                "path": chunk["path"],
                "source_priority": chunk.get("source_priority", "normal"),
                "section": chunk.get("section", "general")
            }
        )

        langchain_documents.append(document)

    # Create FAISS vector store
    print("Creating FAISS vector database...")

    vector_store = FAISS.from_documents(
        langchain_documents,
        embeddings
    )

    # Save locally
    vector_store.save_local("faiss_index")

    print("\nVector database created successfully! ✅")
    print("Saved to: faiss_index/")

    return vector_store


if __name__ == "__main__":

    create_vector_store()