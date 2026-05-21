import math
from typing import Annotated
from fastapi import APIRouter, Depends, status, Query
from src.core.dependencies import get_current_user
from src.modules.users.models import User
from src.modules.books.models import GenreEnum
from src.modules.books.schemas import (
    BookCreate, BookUpdate, BookResponse, BookListResponse,
    AuthorCreate, AuthorResponse
)
from src.modules.books.services import BookService, AuthorService

router = APIRouter(prefix="/books", tags=["Books"])
author_router = APIRouter(prefix="/authors", tags=["Authors"])


@author_router.post("", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
async def create_author(
    data: AuthorCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    author_service: AuthorService = Depends(AuthorService)
):
    """
    Create a new author. Requires JWT authentication.
    """
    return await author_service.create_author(data)


@author_router.get("", response_model=list[AuthorResponse])
async def list_authors(
    author_service: AuthorService = Depends(AuthorService)
):
    """
    Retrieve all authors in alphabetical order. Public endpoint.
    """
    return await author_service.list_authors()


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: BookCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    book_service: BookService = Depends(BookService)
):
    """
    Create a new book and associate it with existing authors. Requires JWT authentication.
    """
    return await book_service.create_book(data)


@router.get("", response_model=BookListResponse)
async def list_books(
    page: int = Query(default=1, ge=1, description="Page number starting from 1"),
    per_page: int = Query(default=10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(default="id", description="Field to sort by (id, title, publication_year, genre)"),
    sort_order: str = Query(default="asc", description="Sort direction (asc, desc)"),
    title: str | None = Query(default=None, description="Filter by book title (case-insensitive substring)"),
    author: str | None = Query(default=None, description="Filter by author name (case-insensitive substring)"),
    genre: GenreEnum | None = Query(default=None, description="Filter by genre"),
    min_year: int | None = Query(default=None, ge=1800, le=2026, description="Minimum publication year"),
    max_year: int | None = Query(default=None, ge=1800, le=2026, description="Maximum publication year"),
    book_service: BookService = Depends(BookService)
):
    """
    List all books with support for pagination, sorting, and advanced filtering. Public endpoint.
    """
    items, total = await book_service.list_books(
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
        title=title,
        author=author,
        genre=genre,
        min_year=min_year,
        max_year=max_year
    )
    pages = math.ceil(total / per_page) if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page
    }


@router.get("/{id}", response_model=BookResponse)
async def get_book(
    id: int,
    book_service: BookService = Depends(BookService)
):
    """
    Get a single book details by ID. Public endpoint.
    """
    return await book_service.get_book_by_id(id)


@router.put("/{id}", response_model=BookResponse)
async def update_book(
    id: int,
    data: BookUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    book_service: BookService = Depends(BookService)
):
    """
    Update a book's metadata or author associations. Requires JWT authentication.
    """
    return await book_service.update_book(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    book_service: BookService = Depends(BookService)
):
    """
    Delete a book by ID. Requires JWT authentication.
    """
    await book_service.delete_book(id)
