from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import Depends
from src.core.database import get_db
from src.modules.books.models import Book, Author, GenreEnum

class AuthorRepository:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def create(self, author: Author) -> Author:
        self.db.add(author)
        await self.db.commit()
        await self.db.refresh(author)
        return author

    async def get_by_name(self, name: str) -> Author | None:
        result = await self.db.execute(select(Author).where(func.lower(Author.name) == name.lower()))
        return result.scalar_one_or_none()

    async def get_by_id(self, author_id: int) -> Author | None:
        result = await self.db.execute(select(Author).where(Author.id == author_id))
        return result.scalar_one_or_none()

    async def get_by_ids(self, author_ids: list[int]) -> list[Author]:
        if not author_ids:
            return []
        result = await self.db.execute(select(Author).where(Author.id.in_(author_ids)))
        return list(result.scalars().all())

    async def list_authors(self) -> list[Author]:
        result = await self.db.execute(select(Author).order_by(Author.name.asc()))
        return list(result.scalars().all())


class BookRepository:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def create(self, book: Book) -> Book:
        self.db.add(book)
        await self.db.commit()
        return await self.get_by_id(book.id)

    async def get_by_id(self, book_id: int) -> Book | None:
        stmt = (
            select(Book)
            .options(selectinload(Book.authors))
            .where(Book.id == book_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_books(
        self,
        offset: int,
        limit: int,
        sort_by: str,
        sort_order: str,
        title: str | None = None,
        author_name: str | None = None,
        genre: GenreEnum | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
    ) -> tuple[list[Book], int]:
        stmt = select(Book).options(selectinload(Book.authors))
        count_stmt = select(func.count(Book.id))

        filters = []
        if title:
            filters.append(Book.title.ilike(f"%{title}%"))
        if genre:
            filters.append(Book.genre == genre)
        if min_year is not None:
            filters.append(Book.publication_year >= min_year)
        if max_year is not None:
            filters.append(Book.publication_year <= max_year)
        if author_name:
            filters.append(Book.authors.any(Author.name.ilike(f"%{author_name}%")))

        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        allowed_sort_fields = {
            "title": Book.title,
            "publication_year": Book.publication_year,
            "genre": Book.genre,
            "id": Book.id,
        }

        sort_field = allowed_sort_fields.get(sort_by.lower(), Book.id)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(sort_field.desc())
        else:
            stmt = stmt.order_by(sort_field.asc())

        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        books = list(result.scalars().all())

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        return books, total

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, obj: Book) -> None:
        await self.db.refresh(obj)

    async def delete(self, book: Book) -> None:
        await self.db.delete(book)
        await self.db.commit()

    async def list_all_books_for_export(self) -> list[Book]:
        stmt = select(Book).options(selectinload(Book.authors)).order_by(Book.id.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
