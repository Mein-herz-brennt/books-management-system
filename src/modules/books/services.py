from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from src.modules.books.models import Book, Author, GenreEnum
from src.modules.books.schemas import BookCreate, BookUpdate, AuthorCreate
from src.modules.books.repositories import BookRepository, AuthorRepository
from datetime import datetime
import json
import csv
import io


class AuthorService:
    def __init__(self, author_repo: AuthorRepository = Depends(AuthorRepository)):
        self.author_repo = author_repo

    async def create_author(self, data: AuthorCreate) -> Author:
        existing_author = await self.author_repo.get_by_name(data.name)
        if existing_author:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Author with name '{data.name}' already exists"
            )

        try:
            new_author = Author(
                name=data.name,
                bio=data.bio
            )
            return await self.author_repo.create(new_author)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Author with name '{data.name}' already exists"
            )

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

    async def import_books(self, file_content: bytes, filename: str) -> dict:
        records = []
        if filename.endswith('.json'):
            try:
                data = json.loads(file_content.decode('utf-8'))
                if not isinstance(data, list):
                    raise HTTPException(status_code=400, detail="JSON must be an array of book objects")
                records = data
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON file format")
        elif filename.endswith('.csv'):
            try:
                decoded = file_content.decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                for row in reader:
                    authors_str = row.get('authors', '')
                    authors_list = [a.strip() for a in authors_str.replace(';', ',').split(',') if a.strip()]
                    
                    year_str = row.get('publication_year', '')
                    try:
                        year = int(year_str) if year_str else 0
                    except ValueError:
                        year = 0
                        
                    records.append({
                        "title": row.get('title', ''),
                        "genre": row.get('genre', ''),
                        "publication_year": year,
                        "authors": authors_list
                    })
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid CSV file format: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload JSON or CSV.")
            
        if not records:
            raise HTTPException(status_code=400, detail="No records found in file")

        imported_count = 0
        current_year = datetime.now().year
        
        try:
            for idx, rec in enumerate(records):
                title = rec.get('title', '').strip()
                genre_str = rec.get('genre', '').strip()
                pub_year = rec.get('publication_year')
                author_names = rec.get('authors', [])
                
                if not title:
                    raise HTTPException(status_code=400, detail=f"Record {idx+1}: Title must not be empty")
                
                try:
                    genre = GenreEnum(genre_str)
                except ValueError:
                    allowed = [g.value for g in GenreEnum]
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Record {idx+1}: Invalid genre '{genre_str}'. Allowed genres: {allowed}"
                    )
                
                if not isinstance(pub_year, int) or pub_year < 1800 or pub_year > current_year:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Record {idx+1}: Publication year must be between 1800 and {current_year}"
                    )
                
                authors_db = []
                for a_name in author_names:
                    a_name = a_name.strip()
                    if not a_name:
                        continue
                    author = await self.author_repo.get_by_name(a_name)
                    if not author:
                        author = Author(name=a_name)
                        author = await self.author_repo.create(author)
                    authors_db.append(author)
                
                book = Book(
                    title=title,
                    genre=genre,
                    publication_year=pub_year,
                    authors=authors_db
                )
                await self.book_repo.create(book)
                imported_count += 1
                
            await self.book_repo.commit()
            return {"status": "success", "imported": imported_count}
            
        except HTTPException as he:
            await self.book_repo.db.rollback()
            raise he
        except IntegrityError as ie:
            await self.book_repo.db.rollback()
            raise HTTPException(status_code=400, detail=f"Integrity error during import: {str(ie.orig)}")
        except Exception as e:
            await self.book_repo.db.rollback()
            raise HTTPException(status_code=500, detail=f"An error occurred during import: {str(e)}")

    async def export_books(self, format: str) -> tuple[bytes, str]:
        books = await self.book_repo.list_all_books_for_export()
        
        if format.lower() == 'json':
            data = []
            for b in books:
                data.append({
                    "id": b.id,
                    "title": b.title,
                    "genre": b.genre.value if hasattr(b.genre, 'value') else str(b.genre),
                    "publication_year": b.publication_year,
                    "authors": [a.name for a in b.authors]
                })
            content = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
            return content, "application/json"
            
        elif format.lower() == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "title", "genre", "publication_year", "authors"])
            for b in books:
                genre_str = b.genre.value if hasattr(b.genre, 'value') else str(b.genre)
                authors_str = "; ".join([a.name for a in b.authors])
                writer.writerow([b.id, b.title, genre_str, b.publication_year, authors_str])
            content = output.getvalue().encode('utf-8')
            return content, "text/csv"
            
        else:
            raise HTTPException(status_code=400, detail="Invalid export format. Supported formats: json, csv")
