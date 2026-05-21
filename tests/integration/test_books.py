import pytest
from fastapi import status
from src.modules.auth.service import TokenService
from src.modules.books.models import GenreEnum, Book, Author
from sqlalchemy import select

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
    response = await client.put(f"/api/v1/books/{book.id}", json=payload, headers=headers)
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
