
from pydantic import BaseModel, HttpUrl, ConfigDict


class RepositoryCreate(BaseModel):
    name: str
    github_url: HttpUrl


class RepositoryResponse(BaseModel):
    id: int
    name: str
    github_url: str
    user_id: int

    model_config = ConfigDict(from_attributes=True)
