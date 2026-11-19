
from pydantic import BaseModel, Field


# =========================================
# ASK QUESTION REQUEST
# =========================================

class AskRequest(BaseModel):
    conversation_id: int
    question: str = Field(
        min_length=1,
        max_length=10000
    )


# =========================================
# ASK QUESTION RESPONSE
# =========================================

class AskResponse(BaseModel):
    conversation_id: int
    repository_id: int
    repository_name: str
    question: str
    answer: str
    sources: list[dict] = []
