
import asyncio
import traceback
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.app.db.database import get_db
from backend.app.core.dependencies import get_current_user

from backend.app.models.user import User
from backend.app.models.repository import Repository
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
)
from backend.app.schemas.chat import AskRequest

from backend.app.services.github_service import (
    WORKSPACE_DIR,
    clone_repository,
    remove_directory,
)
from backend.app.services.rag_service import index_repository

from core.rag import generate_answer
from core.retrieval import invalidate_vector_store_cache


router = APIRouter(prefix="/repositories", tags=["Repositories"])

# In-memory tracker for long-running index/reindex background jobs
_indexing_jobs: dict[int, dict] = {}
_indexing_tasks: set[asyncio.Task] = set()


def _get_workspace_paths(user_id: int, repository_id: int) -> tuple[Path, Path]:
    base_path = WORKSPACE_DIR.resolve()
    workspace_path = (
        base_path
        / f"user_{user_id}"
        / f"repository_{repository_id}"
    ).resolve()
    workspace_path.relative_to(base_path)
    return base_path, workspace_path


def _is_repo_indexed(workspace_path: Path) -> bool:
    index_dir = workspace_path / "faiss_index"
    return (
        (index_dir / "index.faiss").exists()
        and (index_dir / "index.pkl").exists()
    )


def _make_progress_callback(repository_id: int):
    def _on_progress(batch_index: int, total_batches: int, processed: int, total: int):
        job = _indexing_jobs.get(repository_id)
        if job is not None:
            job["stage"] = "indexing"
            job["message"] = (
                f"Embedding batch {batch_index}/{total_batches} "
                f"({processed}/{total} chunks)..."
            )
    return _on_progress


async def _run_index_task(
    repository_id: int,
    user_id: int,
    repository_name: str,
) -> None:
    try:
        _indexing_jobs[repository_id] = {
            "repository_id": repository_id,
            "repository_name": repository_name,
            "status": "processing",
            "stage": "indexing",
            "message": "Processing files and generating FAISS embeddings...",
        }

        indexing_result = await run_in_threadpool(
            index_repository,
            user_id,
            repository_id,
            _make_progress_callback(repository_id),
        )

        _indexing_jobs[repository_id] = {
            "repository_id": repository_id,
            "repository_name": repository_name,
            "status": "completed",
            "stage": "completed",
            "message": "Repository indexed successfully.",
            "indexed": True,
            **indexing_result,
        }

    except Exception as exc:
        print("\n========== BACKGROUND INDEXING ERROR ==========")
        traceback.print_exc()
        print("===============================================\n")
        _indexing_jobs[repository_id] = {
            "repository_id": repository_id,
            "repository_name": repository_name,
            "status": "failed",
            "stage": "failed",
            "message": str(exc) or "Repository indexing failed.",
            "error": str(exc) or "Repository indexing failed.",
        }


async def _run_reindex_task(
    repository_id: int,
    user_id: int,
    repository_name: str,
    github_url: str,
) -> None:
    backup_path = None
    backup_created = False
    workspace_path = None

    try:
        base_path, workspace_path = _get_workspace_paths(user_id, repository_id)
        backup_path = workspace_path.with_name(
            f"{workspace_path.name}_backup_{uuid.uuid4().hex}"
        )
        backup_path.relative_to(base_path)

        print(f"[REINDEX] Starting re-index for repository {repository_id} ({repository_name})")

        _indexing_jobs[repository_id] = {
            "repository_id": repository_id,
            "repository_name": repository_name,
            "status": "processing",
            "stage": "cloning",
            "message": "Cloning latest GitHub repository...",
        }

        invalidate_vector_store_cache(workspace_path / "faiss_index")

        if workspace_path.exists():
            await run_in_threadpool(workspace_path.rename, backup_path)
            backup_created = True

        await run_in_threadpool(
            clone_repository,
            github_url,
            user_id,
            repository_id,
        )
        print(f"[REINDEX] Cloned repository {repository_id}. Starting indexing...")

        _indexing_jobs[repository_id]["stage"] = "indexing"
        _indexing_jobs[repository_id]["message"] = (
            "Processing files and generating FAISS embeddings..."
        )

        indexing_result = await run_in_threadpool(
            index_repository,
            user_id,
            repository_id,
            _make_progress_callback(repository_id),
        )
        print(
            f"[REINDEX] Completed repository {repository_id}: "
            f"{indexing_result.get('documents_processed')} docs, "
            f"{indexing_result.get('chunks_created')} chunks."
        )

        if backup_created and backup_path is not None:
            try:
                await run_in_threadpool(remove_directory, backup_path)
                backup_created = False
            except OSError:
                print(
                    "Warning: New index created successfully, "
                    "but old workspace backup could not be removed:",
                    backup_path,
                )

        _indexing_jobs[repository_id] = {
            "repository_id": repository_id,
            "repository_name": repository_name,
            "status": "completed",
            "stage": "completed",
            "message": "Repository re-indexed successfully.",
            "indexed": True,
            **indexing_result,
        }

    except Exception as exc:
        print("\n========== RE-INDEXING ERROR ==========")
        traceback.print_exc()
        print("========================================\n")

        if workspace_path is not None and workspace_path.exists():
            try:
                await run_in_threadpool(remove_directory, workspace_path)
            except OSError:
                print("Warning: Failed workspace cleanup failed.")

        if backup_created and backup_path is not None and backup_path.exists() and workspace_path is not None:
            try:
                await run_in_threadpool(backup_path.rename, workspace_path)
                print("Previous repository workspace restored.")
            except OSError:
                print(
                    "CRITICAL: Could not restore previous workspace:",
                    backup_path,
                )

        _indexing_jobs[repository_id] = {
            "repository_id": repository_id,
            "repository_name": repository_name,
            "status": "failed",
            "stage": "failed",
            "message": str(exc) or "Repository re-indexing failed.",
            "error": str(exc) or "Repository re-indexing failed.",
        }


# =========================================
# ADD A GITHUB REPOSITORY
# =========================================

@router.post(
    "/",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_repository(
    data: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    github_url = str(data.github_url).rstrip("/")

    # Prevent duplicate repositories for the same user
    result = await db.execute(
        select(Repository).where(
            Repository.github_url == github_url,
            Repository.user_id == current_user.id
        )
    )

    existing_repo = result.scalar_one_or_none()

    if existing_repo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already added this repository."
        )

    new_repository = Repository(
        name=data.name,
        github_url=github_url,
        user_id=current_user.id
    )

    db.add(new_repository)
    await db.commit()
    await db.refresh(new_repository)

    return new_repository


# =========================================
# LIST USER REPOSITORIES
# =========================================

def _serialize_repository(repository: Repository, user_id: int) -> dict:
    _, workspace_path = _get_workspace_paths(user_id, repository.id)
    return {
        "id": repository.id,
        "name": repository.name,
        "github_url": repository.github_url,
        "user_id": repository.user_id,
        "indexed": _is_repo_indexed(workspace_path),
    }


@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Repository)
        .where(Repository.user_id == current_user.id)
        .order_by(Repository.id.desc())
    )

    repositories = result.scalars().all()
    return [
        _serialize_repository(repo, current_user.id)
        for repo in repositories
    ]


# =========================================
# GET ONE REPOSITORY
# =========================================

@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == current_user.id
        )
    )

    repository = result.scalar_one_or_none()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    return _serialize_repository(repository, current_user.id)


# =========================================
# DELETE REPOSITORY AND ASSOCIATED DATA
# =========================================

@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify repository ownership
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == current_user.id
        )
    )

    repository = result.scalar_one_or_none()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    # 2. Find associated conversations
    conversation_result = await db.execute(
        select(Conversation).where(
            Conversation.repository_id == repository_id,
            Conversation.user_id == current_user.id
        )
    )

    conversations = conversation_result.scalars().all()

    conversation_ids = [
        conversation.id for conversation in conversations
    ]

    # 3. Delete associated messages
    if conversation_ids:
        message_result = await db.execute(
            select(Message).where(
                Message.conversation_id.in_(conversation_ids)
            )
        )

        messages = message_result.scalars().all()

        for message in messages:
            await db.delete(message)

    # 4. Delete conversations
    for conversation in conversations:
        await db.delete(conversation)

    # 5. Delete repository record
    await db.delete(repository)

    await db.commit()

    # 6. Remove cloned repository and FAISS index
    base_path = WORKSPACE_DIR.resolve()

    workspace_path = (
        base_path
        / f"user_{current_user.id}"
        / f"repository_{repository_id}"
    ).resolve()

    try:
        # Ensure the target is inside the workspace directory
        workspace_path.relative_to(base_path)
        invalidate_vector_store_cache(workspace_path / "faiss_index")
        _indexing_jobs.pop(repository_id, None)

        if workspace_path.exists():
            await run_in_threadpool(
                remove_directory,
                workspace_path
            )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid repository workspace path."
        )

    except OSError:
        return {
            "message": (
                "Repository and database records deleted, "
                "but workspace cleanup failed."
            ),
            "repository_id": repository_id,
            "workspace_cleanup": "failed"
        }

    return {
        "message": "Repository and associated data deleted successfully.",
        "repository_id": repository_id,
        "workspace_cleanup": "successful"
    }


# =========================================
# CLONE GITHUB REPOSITORY
# =========================================

@router.post("/{repository_id}/clone")
async def clone_github_repository(
    repository_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == current_user.id
        )
    )

    repository = result.scalar_one_or_none()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    try:
        local_path = await run_in_threadpool(
            clone_repository,
            repository.github_url,
            current_user.id,
            repository.id
        )

        return {
            "message": "Repository cloned successfully.",
            "repository_id": repository.id,
            "repository_name": repository.name,
            "local_path": local_path
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )

    except FileExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc)
        )


# =========================================
# GET INDEXING / RE-INDEXING STATUS
# =========================================

@router.get("/{repository_id}/status")
async def get_repository_status(
    repository_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == current_user.id
        )
    )

    repository = result.scalar_one_or_none()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    job = _indexing_jobs.get(repository_id)
    if job is not None:
        return job

    _, workspace_path = _get_workspace_paths(current_user.id, repository_id)
    indexed = _is_repo_indexed(workspace_path)

    return {
        "repository_id": repository.id,
        "repository_name": repository.name,
        "status": "completed" if indexed else "idle",
        "stage": "completed" if indexed else "idle",
        "indexed": indexed,
        "message": (
            "Repository is indexed and ready."
            if indexed
            else "Repository has not been indexed yet."
        ),
    }


# =========================================
# INDEX GITHUB REPOSITORY
# =========================================

@router.post("/{repository_id}/index")
async def index_github_repository(
    repository_id: int,
    background: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == current_user.id
        )
    )

    repository = result.scalar_one_or_none()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    existing_job = _indexing_jobs.get(repository_id)
    if existing_job and existing_job.get("status") == "processing":
        return existing_job

    if background:
        task = asyncio.create_task(
            _run_index_task(
                repository_id=repository.id,
                user_id=current_user.id,
                repository_name=repository.name,
            )
        )
        _indexing_tasks.add(task)
        task.add_done_callback(_indexing_tasks.discard)

        return {
            "status": "processing",
            "stage": "indexing",
            "message": "Repository indexing started.",
            "repository_id": repository.id,
            "repository_name": repository.name,
        }

    try:
        indexing_result = await run_in_threadpool(
            index_repository,
            current_user.id,
            repository.id
        )

        return {
            "message": "Repository indexed successfully.",
            "repository_name": repository.name,
            **indexing_result
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )

    except Exception:
        print("\n========== REPOSITORY INDEXING ERROR ==========")
        traceback.print_exc()
        print("================================================\n")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository indexing failed. Check the backend terminal."
        )




# =========================================
# RE-INDEX EXISTING GITHUB REPOSITORY
# =========================================

@router.post(
    "/{repository_id}/reindex",
    status_code=status.HTTP_202_ACCEPTED
)
async def reindex_github_repository(
    repository_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify repository ownership
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == current_user.id
        )
    )

    repository = result.scalar_one_or_none()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    existing_job = _indexing_jobs.get(repository_id)
    if existing_job and existing_job.get("status") == "processing":
        return existing_job

    task = asyncio.create_task(
        _run_reindex_task(
            repository_id=repository.id,
            user_id=current_user.id,
            repository_name=repository.name,
            github_url=repository.github_url,
        )
    )
    _indexing_tasks.add(task)
    task.add_done_callback(_indexing_tasks.discard)

    return {
        "status": "processing",
        "stage": "queued",
        "message": "Repository re-indexing started.",
        "repository_id": repository.id,
        "repository_name": repository.name,
    }

# =========================================
# ASK QUESTIONS ABOUT REPOSITORY
# =========================================

@router.post("/{repository_id}/ask")
async def ask_repository(
    repository_id: int,
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify repository ownership
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == current_user.id
        )
    )

    repository = result.scalar_one_or_none()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    # 2. Verify conversation ownership and repository association
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.repository_id == repository_id
        )
    )

    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found for this repository."
        )

    # 3. Locate the repository's FAISS index
    index_path = (
        WORKSPACE_DIR
        / f"user_{current_user.id}"
        / f"repository_{repository_id}"
        / "faiss_index"
    )

    if not index_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository has not been indexed yet."
        )

    # 4. Generate AI response
    try:
        rag_result = await run_in_threadpool(
            generate_answer,
            request.question,
            str(index_path)
        )

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    except AssertionError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "FAISS index is incompatible with the current embedding model. "
                "Please click Re-index on this repository."
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate answer: {str(error)}"
        )

    answer, sources = rag_result

    # 5. Save user question
    user_message = Message(
        role="user",
        content=request.question,
        conversation_id=conversation.id
    )

    # Generate title from the first question
    if conversation.title == "New Conversation":

        conversation.title = request.question.strip()[:60]

        if len(request.question.strip()) > 60:
            conversation.title += "..."

    # 6. Save AI response
    assistant_message = Message(
        role="assistant",
        content=answer,
        conversation_id=conversation.id
    )

    db.add_all([user_message, assistant_message])

    # 7. Save messages in PostgreSQL
    await db.commit()

    return {
        "conversation_id": conversation.id,
        "repository_id": repository.id,
        "repository_name": repository.name,
        "question": request.question,
        "answer": answer,
        "sources": sources
    }
