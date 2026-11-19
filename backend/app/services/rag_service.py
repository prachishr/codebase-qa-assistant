
from pathlib import Path

from core.ingestion import load_repository
from core.chunking import create_chunks
from core.vector_store import create_vector_store


WORKSPACE_DIR = Path(__file__).resolve().parents[3] / "workspaces"


def index_repository(user_id: int, repository_id: int):
    """
    Load, chunk, and index a cloned GitHub repository.
    Each repository gets its own FAISS index.
    """

    repository_path = (
        WORKSPACE_DIR
        / f"user_{user_id}"
        / f"repository_{repository_id}"
    )

    if not repository_path.exists():
        raise FileNotFoundError("Repository has not been cloned yet.")

    index_path = repository_path / "faiss_index"

    # Step 1: Load repository documents
    documents = load_repository(str(repository_path))

    if not documents:
        raise ValueError("No supported documents found in this repository.")

    # Step 2: Split documents into chunks
    chunks = create_chunks(
        documents,
        repo_path=str(repository_path)
    )

    # Diagnostic: Check README project overview chunks
    overview_chunks = [
        chunk for chunk in chunks
        if chunk.get("section") == "project_overview"
    ]

    print(f"Project overview chunks: {len(overview_chunks)}")

    for chunk in overview_chunks:
        print(f"Overview file: {chunk['file']}")
        print(f"Overview path: {chunk['path']}")

    if not chunks:
        raise ValueError("No chunks were generated from this repository.")

    # Step 3: Create and save the FAISS index
    create_vector_store(
        chunks,
        index_path=str(index_path)
    )

    return {
        "repository_id": repository_id,
        "documents_processed": len(documents),
        "chunks_created": len(chunks),
        "index_path": str(index_path)
    }
