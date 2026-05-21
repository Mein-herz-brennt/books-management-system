from pydantic import BaseModel, Field, field_validator
from src.modules.books.models import GenreEnum

class AuthorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    bio: str | None = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name must not be empty or only whitespace')
        return v.strip()

    @field_validator('bio')
    @classmethod
    def validate_bio(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            return None
        return v.strip() if v is not None else None


class AuthorResponse(BaseModel):
    id: int
    name: str
    bio: str | None

    class Config:
        from_attributes = True


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    genre: GenreEnum
    publication_year: int = Field(..., ge=1800, le=2026)
    author_ids: list[int] = Field(default_factory=list)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Title must not be empty or only whitespace')
        return v.strip()


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    genre: GenreEnum | None = None
    publication_year: int | None = Field(default=None, ge=1800, le=2026)
    author_ids: list[int] | None = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                raise ValueError('Title must not be empty or only whitespace')
            return v.strip()
        return v


class BookResponse(BaseModel):
    id: int
    title: str
    genre: GenreEnum
    publication_year: int
    authors: list[AuthorResponse]

    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    pages: int
    per_page: int

    class Config:
        from_attributes = True
