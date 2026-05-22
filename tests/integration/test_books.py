import pytest
from fastapi import status
from src.modules.auth.service import TokenService
from src.modules.books.models import GenreEnum, Book, Author
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def get_auth_headers(create_test_user, username="testadmin", password="password"):
    user = await create_test_user(username=username, password=password)
    access_token = TokenService.create_access_token(user.username)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_create_author_success(client, create_test_user):
    headers = await get_auth_headers(create_test_user)
    payload = {
        "name": "J.K. Rowling",
        "bio": "British author best known for Harry Potter."
    }
    response = await client.post("/api/v1/authors", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "J.K. Rowling"
    assert data["bio"] == "British author best known for Harry Potter."
    assert "id" in data


@pytest.mark.asyncio
async def test_create_author_unauthorized(client):
    payload = {
        "name": "Unauthorized Author",
        "bio": "No headers."
    }
    response = await client.post("/api/v1/authors", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_author_validation_empty_name(client, create_test_user):
    headers = await get_auth_headers(create_test_user)
    payload = {
        "name": "   ",
        "bio": "Bio content."
    }
    response = await client.post("/api/v1/authors", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_book_success(client, db_session, create_test_user):
    headers = await get_auth_headers(create_test_user)
    
    # Pre-create an author
    author = Author(name="J.R.R. Tolkien", bio="Father of fantasy.")
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)

    payload = {
        "title": "The Hobbit",
        "genre": GenreEnum.FANTASY.value,
        "publication_year": 1937,
        "author_ids": [author.id]
    }
    response = await client.post("/api/v1/books", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "The Hobbit"
    assert data["genre"] == GenreEnum.FANTASY.value
    assert data["publication_year"] == 1937
    assert len(data["authors"]) == 1
    assert data["authors"][0]["id"] == author.id


@pytest.mark.asyncio
async def test_create_book_invalid_author_id(client, create_test_user):
    headers = await get_auth_headers(create_test_user)
    payload = {
        "title": "Invalid Author Book",
        "genre": GenreEnum.FICTION.value,
        "publication_year": 2000,
        "author_ids": [9999]
    }
    response = await client.post("/api/v1/books", json=payload, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "do not exist" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_book_validation_year(client, create_test_user):
    headers = await get_auth_headers(create_test_user)
    
    # Under limit (1799)
    payload = {
        "title": "Old Book",
        "genre": GenreEnum.HISTORY.value,
        "publication_year": 1799,
        "author_ids": []
    }
    response = await client.post("/api/v1/books", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Over limit (2027)
    payload = {
        "title": "Future Book",
        "genre": GenreEnum.SCI_FI.value,
        "publication_year": 2027,
        "author_ids": []
    }
    response = await client.post("/api/v1/books", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_book_validation_empty_title(client, create_test_user):
    headers = await get_auth_headers(create_test_user)
    payload = {
        "title": "   ",
        "genre": GenreEnum.FICTION.value,
        "publication_year": 2020,
        "author_ids": []
    }
    response = await client.post("/api/v1/books", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_get_book_success(client, db_session):
    # Setup database state
    author = Author(name="Stephen King", bio="Horror writer.")
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)

    book = Book(title="The Shining", genre=GenreEnum.MYSTERY, publication_year=1977, authors=[author])
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)

    response = await client.get(f"/api/v1/books/{book.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "The Shining"
    assert data["authors"][0]["name"] == "Stephen King"


@pytest.mark.asyncio
async def test_get_book_not_found(client):
    response = await client.get("/api/v1/books/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_book_success(client, db_session, create_test_user):
    headers = await get_auth_headers(create_test_user)
    
    author1 = Author(name="Author One", bio="Bio One")
    author2 = Author(name="Author Two", bio="Bio Two")
    db_session.add_all([author1, author2])
    await db_session.commit()
    await db_session.refresh(author1)
    await db_session.refresh(author2)
    book = Book(title="Original Title", genre=GenreEnum.FICTION, publication_year=2000, authors=[author1])
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)

    payload = {
        "title": "Updated Title",
        "genre": GenreEnum.SCI_FI.value,
        "publication_year": 2010,
        "author_ids": [author2.id]
    }
    response = await client.patch(f"/api/v1/books/{book.id}", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["genre"] == GenreEnum.SCI_FI.value
    assert data["publication_year"] == 2010
    assert len(data["authors"]) == 1
    assert data["authors"][0]["id"] == author2.id


@pytest.mark.asyncio
async def test_delete_book_success(client, db_session, create_test_user):
    headers = await get_auth_headers(create_test_user)
    
    book = Book(title="Temporary Book", genre=GenreEnum.BIOGRAPHY, publication_year=2015, authors=[])
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)

    response = await client.delete(f"/api/v1/books/{book.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    stmt = select(Book).where(Book.id == book.id)
    res = await db_session.execute(stmt)
    assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_list_books_pagination_and_filters(client, db_session):
    author_sci_fi = Author(name="SciFi Expert")
    author_mystery = Author(name="Mystery Guru")
    db_session.add_all([author_sci_fi, author_mystery])
    await db_session.commit()
    await db_session.refresh(author_sci_fi)
    await db_session.refresh(author_mystery)

    book1 = Book(title="Alpha Space", genre=GenreEnum.SCI_FI, publication_year=1995, authors=[author_sci_fi])
    book2 = Book(title="Beta Mystery", genre=GenreEnum.MYSTERY, publication_year=2005, authors=[author_mystery])
    book3 = Book(title="Gamma Space Journey", genre=GenreEnum.SCI_FI, publication_year=2015, authors=[author_sci_fi])
    db_session.add_all([book1, book2, book3])
    await db_session.commit()

    response = await client.get("/api/v1/books")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    response = await client.get("/api/v1/books?page=1&per_page=2")
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["pages"] == 2

    response = await client.get("/api/v1/books?title=space")
    data = response.json()
    assert data["total"] == 2
    titles = [b["title"] for b in data["items"]]
    assert "Alpha Space" in titles
    assert "Gamma Space Journey" in titles

    response = await client.get("/api/v1/books?author=Guru")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Beta Mystery"

    response = await client.get(f"/api/v1/books?genre={GenreEnum.SCI_FI.value}")
    data = response.json()
    assert data["total"] == 2

    response = await client.get("/api/v1/books?min_year=2000&max_year=2010")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Beta Mystery"

    response = await client.get("/api/v1/books?sort_by=title&sort_order=desc")
    data = response.json()
    titles = [b["title"] for b in data["items"]]
    assert titles == ["Gamma Space Journey", "Beta Mystery", "Alpha Space"]

    response = await client.get("/api/v1/books?sort_by=publication_year&sort_order=asc")
    data = response.json()
    titles = [b["title"] for b in data["items"]]
    assert titles == ["Alpha Space", "Beta Mystery", "Gamma Space Journey"]


@pytest.mark.asyncio
async def test_patch_book_partial(client, db_session, create_test_user):
    headers = await get_auth_headers(create_test_user)
    author = Author(name="Patch Author")
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)
    
    book = Book(title="Original Title", genre=GenreEnum.FICTION, publication_year=2000, authors=[author])
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)

    # Update only title
    response = await client.patch(f"/api/v1/books/{book.id}", json={"title": "New Title Only"}, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "New Title Only"
    assert data["genre"] == GenreEnum.FICTION.value
    assert data["publication_year"] == 2000
    assert len(data["authors"]) == 1
    assert data["authors"][0].get("id") == author.id


@pytest.mark.asyncio
async def test_import_books_json_success(client, db_session, create_test_user):
    headers = await get_auth_headers(create_test_user)
    
    import json
    import datetime
    
    current_year = datetime.datetime.now().year
    books_data = [
        {
            "title": "Imported JSON Book 1",
            "genre": "Fiction",
            "publication_year": 2020,
            "authors": ["New Author A", "New Author B"]
        },
        {
            "title": "Imported JSON Book 2",
            "genre": "Mystery",
            "publication_year": current_year,
            "authors": ["New Author A"]
        }
    ]
    
    file_content = json.dumps(books_data).encode("utf-8")
    files = {"file": ("import.json", file_content, "application/json")}
    
    response = await client.post("/api/v1/books/import", files=files, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "success"
    assert data["imported"] == 2
    

    result = await db_session.execute(
        select(Book).options(selectinload(Book.authors)).where(Book.title == "Imported JSON Book 1")
    )
    book1 = result.scalar_one_or_none()
    assert book1 is not None
    assert book1.genre == GenreEnum.FICTION
    
    # Verify authors were created and linked
    assert len(book1.authors) == 2
    author_names = {a.name for a in book1.authors}
    assert "New Author A" in author_names
    assert "New Author B" in author_names


@pytest.mark.asyncio
async def test_import_books_csv_success(client, db_session, create_test_user):
    headers = await get_auth_headers(create_test_user)
    
    csv_content = (
        "title,genre,publication_year,authors\n"
        "CSV Book 1,Science Fiction,2021,Author C\n"
        "CSV Book 2,Biography,2022,\"Author C; Author D\"\n"
    ).encode("utf-8")
    
    files = {"file": ("import.csv", csv_content, "text/csv")}
    response = await client.post("/api/v1/books/import", files=files, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "success"
    assert data["imported"] == 2
    
    result = await db_session.execute(
        select(Book).options(selectinload(Book.authors)).where(Book.title == "CSV Book 2")
    )
    book2 = result.scalar_one_or_none()
    assert book2 is not None
    assert len(book2.authors) == 2
    author_names = {a.name for a in book2.authors}
    assert "Author C" in author_names
    assert "Author D" in author_names


@pytest.mark.asyncio
async def test_import_books_validation_failure(client, create_test_user):
    headers = await get_auth_headers(create_test_user)
    import json
    
    bad_data = [
        {
            "title": "Bad Book",
            "genre": "InvalidGenreName",
            "publication_year": 2020,
            "authors": ["Author X"]
        }
    ]
    file_content = json.dumps(bad_data).encode("utf-8")
    files = {"file": ("import.json", file_content, "application/json")}
    
    response = await client.post("/api/v1/books/import", files=files, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid genre" in response.json()["detail"]


@pytest.mark.asyncio
async def test_export_books_all_formats(client, db_session):
    author = Author(name="Export Author")
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)
    
    book1 = Book(title="Export Book 1", genre=GenreEnum.FICTION, publication_year=2000, authors=[author])
    book2 = Book(title="Export Book 2", genre=GenreEnum.MYSTERY, publication_year=2010, authors=[author])
    db_session.add_all([book1, book2])
    await db_session.commit()
    
    response = await client.get("/api/v1/books/export?format=json")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert len(data) >= 2
    
    response = await client.get("/api/v1/books/export?format=csv")
    assert response.status_code == status.HTTP_200_OK
    assert "text/csv" in response.headers["content-type"]
    csv_text = response.text
    assert "Export Book 1" in csv_text
    assert "Export Book 2" in csv_text
    assert "Export Author" in csv_text


@pytest.mark.asyncio
async def test_health_check_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data


@pytest.mark.asyncio
async def test_create_author_duplicate_validation(client, create_test_user):
    headers = await get_auth_headers(create_test_user)
    
    payload = {"name": "Unique Author", "bio": "First creation."}
    response = await client.post("/api/v1/authors", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    
    response = await client.post("/api/v1/authors", json=payload, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]
