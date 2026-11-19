
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


# =========================================
# CREATE CONVERSATION
# =========================================

class ConversationCreate(BaseModel):
    repository_id: int
    title: str = Field(
        default="New Conversation",
        max_length=255
    )


# =========================================
# CONVERSATION RESPONSE
# =========================================

class ConversationResponse(BaseModel):
    id: int
    title: str
    user_id: int
    repository_id: int
    repository_name: str

    model_config = ConfigDict(from_attributes=True)


# =========================================
# MESSAGE RESPONSE
# =========================================

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    conversation_id: int

    model_config = ConfigDict(from_attributes=True)


# =========================================
# CONVERSATION DETAIL
# =========================================

class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []
