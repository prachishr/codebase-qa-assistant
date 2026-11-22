
import shutil
import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.app.db.database import get_db
from backend.app.core.dependencies import get_current_user

from backend.app.models.user import User
from backend.app.models.repository import Repository
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
import uuid
from backend.app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
)
from backend.app.schemas.chat import AskRequest

from backend.app.services.github_service import (
    WORKSPACE_DIR,
    clone_repository,
)
from backend.app.services.rag_service import index_repository

from core.rag import generate_answer


router = APIRouter(prefix="/repositories", tags=["Repositories"])


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

    return result.scalars().all()


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

    return repository


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

        if workspace_path.exists():
            await run_in_threadpool(
                shutil.rmtree,
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
# INDEX GITHUB REPOSITORY
# =========================================

@router.post("/{repository_id}/index")
async def index_github_repository(
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

@router.post("/{repository_id}/reindex")
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

    # 2. Locate repository workspace
    base_path = WORKSPACE_DIR.resolve()

    workspace_path = (
        base_path
        / f"user_{current_user.id}"
        / f"repository_{repository_id}"
    ).resolve()

    # Create a unique backup path
    backup_path = workspace_path.with_name(
        f"{workspace_path.name}_backup_{uuid.uuid4().hex}"
    )

    backup_created = False

    try:
        # 3. Ensure workspace is inside the allowed directory
        workspace_path.relative_to(base_path)
        backup_path.relative_to(base_path)

        # 4. Preserve existing workspace
        if workspace_path.exists():

            await run_in_threadpool(
                workspace_path.rename,
                backup_path
            )

            backup_created = True

        # 5. Clone latest GitHub repository
        await run_in_threadpool(
            clone_repository,
            repository.github_url,
            current_user.id,
            repository.id
        )

        # 6. Generate fresh FAISS index
        indexing_result = await run_in_threadpool(
            index_repository,
            current_user.id,
            repository.id
        )

        # 7. Remove backup only after successful indexing
        if backup_created:

            try:
                await run_in_threadpool(
                    shutil.rmtree,
                    backup_path
                )

                backup_created = False

            except OSError:
                print(
                    "Warning: New index created successfully, "
                    "but old workspace backup could not be removed:",
                    backup_path
                )

        return {
            "message": "Repository re-indexed successfully.",
            "repository_id": repository.id,
            "repository_name": repository.name,
            **indexing_result
        }

    except Exception as exc:

        print("\n========== RE-INDEXING ERROR ==========")
        traceback.print_exc()
        print("========================================\n")

        # 8. Remove the failed new workspace
        try:
            if workspace_path.exists():
                await run_in_threadpool(
                    shutil.rmtree,
                    workspace_path
                )

        except OSError:
            print("Warning: Failed workspace cleanup failed.")

        # 9. Restore the previous workspace
        if backup_created and backup_path.exists():

            try:
                await run_in_threadpool(
                    backup_path.rename,
                    workspace_path
                )

                print("Previous repository workspace restored.")

            except OSError:
                print(
                    "CRITICAL: Could not restore previous workspace:",
                    backup_path
                )

        # 10. Return appropriate error
        if isinstance(exc, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc)
            )

        if isinstance(exc, FileNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc)
            )

        if isinstance(exc, RuntimeError):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc)
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository re-indexing failed. Check the backend logs."
        )

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
