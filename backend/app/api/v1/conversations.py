
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.repository import Repository
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse
)


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


# =========================================
# CREATE A NEW CONVERSATION
# =========================================

@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = await db.execute(
        select(Repository).where(
            Repository.id == conversation_data.repository_id,
            Repository.user_id == current_user.id
        )
    )

    repository = result.scalar_one_or_none()

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )

    conversation = Conversation(
        title=conversation_data.title,
        user_id=current_user.id,
        repository_id=repository.id
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return {
        "id": conversation.id,
        "title": conversation.title,
        "user_id": conversation.user_id,
        "repository_id": conversation.repository_id,
        "repository_name": repository.name
    }


# =========================================
# GET ALL USER CONVERSATIONS
# =========================================

@router.get(
    "/",
    response_model=list[ConversationResponse]
)
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = await db.execute(
        select(
            Conversation.id,
            Conversation.title,
            Conversation.user_id,
            Conversation.repository_id,
            Repository.name.label("repository_name")
        )
        .join(
            Repository,
            Conversation.repository_id == Repository.id
        )
        .where(
            Conversation.user_id == current_user.id
        )
        .order_by(
            Conversation.id.desc()
        )
    )

    conversations = result.mappings().all()

    return [
        {
            "id": conversation.id,
            "title": conversation.title,
            "user_id": conversation.user_id,
            "repository_id": conversation.repository_id,
            "repository_name": conversation.repository_name
        }
        for conversation in conversations
    ]


# =========================================
# GET A CONVERSATION WITH ITS MESSAGES
# =========================================

@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse
)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.repository),
            selectinload(Conversation.messages)
        )
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )

    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    messages = sorted(
        conversation.messages,
        key=lambda message: message.id
    )

    return {
        "id": conversation.id,
        "title": conversation.title,
        "user_id": conversation.user_id,
        "repository_id": conversation.repository_id,
        "repository_name": conversation.repository.name,
        "messages": messages
    }

# =========================================
# DELETE A CONVERSATION
# =========================================

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.messages)
        )
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )

    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    # Delete associated messages first
    for message in conversation.messages:
        await db.delete(message)

    # Delete the conversation
    await db.delete(conversation)

    await db.commit()

    return {
        "message": "Conversation deleted successfully.",
        "conversation_id": conversation_id
    }
