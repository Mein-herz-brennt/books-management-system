from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class UserBase(BaseModel):
    username: str


class RegisterRequest(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)