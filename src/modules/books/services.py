from fastapi import Depends, HTTPException, status
from src.modules.books.models import Book, Author
from src.modules.books.schemas import BookCreate, BookUpdate, AuthorCreate
from src.modules.books.repositories import BookRepository, AuthorRepository

class AuthorService:
    def __init__(self, author_repo: AuthorRepository = Depends(AuthorRepository)):
        self.author_repo = author_repo

    async def create_author(self, data: AuthorCreate) -> Author:
        authors = await self.author_repo.list_authors()
        if any(a.name.lower() == data.name.lower() for a in authors):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Author with name '{data.name}' already exists"
            )

        new_author = Author(
            name=data.name,
            bio=data.bio
        )
        return await self.author_repo.create(new_author)

    async def list_authors(self) -> list[Author]:
        return await self.author_repo.list_authors()


class BookService:
    def __init__(
        self,
        book_repo: BookRepository = Depends(BookRepository),
        author_repo: AuthorRepository = Depends(AuthorRepository),
    ):
        self.book_repo = book_repo
        self.author_repo = author_repo

    async def create_book(self, data: BookCreate) -> Book:
        authors = []
        if data.author_ids:
            authors = await self.author_repo.get_by_ids(data.author_ids)
            found_ids = {a.id for a in authors}
            missing_ids = set(data.author_ids) - found_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Author(s) with ID(s) {sorted(list(missing_ids))} do not exist."
                )

        new_book = Book(
            title=data.title,
            genre=data.genre,
            publication_year=data.publication_year,
            authors=authors
        )
        return await self.book_repo.create(new_book)

    async def get_book_by_id(self, book_id: int) -> Book:
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found."
            )
        return book

    async def list_books(
        self,
        page: int = 1,
        per_page: int = 10,
        sort_by: str = "id",
        sort_order: str = "asc",
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
    ) -> tuple[list[Book], int]:
        offset = (page - 1) * per_page
        return await self.book_repo.list_books(
            offset=offset,
            limit=per_page,
            sort_by=sort_by,
            sort_order=sort_order,
            title=title,
            author_name=author,
            genre=genre,
            min_year=min_year,
            max_year=max_year,
        )

    async def update_book(self, book_id: int, data: BookUpdate) -> Book:
        book = await self.get_book_by_id(book_id)

        if data.title is not None:
            book.title = data.title
        if data.genre is not None:
            book.genre = data.genre
        if data.publication_year is not None:
            book.publication_year = data.publication_year

        if data.author_ids is not None:
            authors = await self.author_repo.get_by_ids(data.author_ids)
            found_ids = {a.id for a in authors}
            missing_ids = set(data.author_ids) - found_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Author(s) with ID(s) {sorted(list(missing_ids))} do not exist."
                )
            book.authors = authors

        await self.book_repo.commit()
        return await self.get_book_by_id(book_id)

    async def delete_book(self, book_id: int) -> None:
        book = await self.get_book_by_id(book_id)
        await self.book_repo.delete(book)
