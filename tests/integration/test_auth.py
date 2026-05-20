import pytest
from fastapi import status, Depends, HTTPException
from sqlalchemy import select
from src.modules.users.models import User
from src.modules.auth.service import TokenService
from src.core.dependencies import get_current_user
from src.main import app

@app.get("/api/v1/test-protected")
async def protected_route_for_test(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id}


@pytest.mark.asyncio
async def test_register_user_success(client, db_session):
    payload = {
        "username": "newuser",
        "password": "securepassword"
    }
    
    response = await client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == 201
    assert "User created successfully" in data["message"]
    
    result = await db_session.execute(select(User).where(User.username == "newuser"))
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.username == "newuser"


@pytest.mark.asyncio
async def test_register_user_duplicate(client, create_test_user):
    await create_test_user(username="duplicateuser", password="password1")
    
    payload = {
        "username": "duplicateuser",
        "password": "password2"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Username already registered"


@pytest.mark.asyncio
async def test_login_success(client, create_test_user):
    await create_test_user(username="loginuser", password="mypassword")
    
    login_data = {
        "username": "loginuser",
        "password": "mypassword"
    }
    
    response = await client.post("/api/v1/auth/login", data=login_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    
    payload = TokenService.get_access_payload(data["access_token"])
    assert payload["sub"] == "loginuser"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, create_test_user):
    await create_test_user(username="loginuser", password="mypassword")
    
    response = await client.post("/api/v1/auth/login", data={
        "username": "loginuser",
        "password": "wrongpassword"
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect username or password"
    
    response = await client.post("/api/v1/auth/login", data={
        "username": "nonexistent",
        "password": "password"
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_refresh_token_success(client, create_test_user):
    await create_test_user(username="refreshuser", password="password")
    
    refresh_token = TokenService.create_refresh_token("refreshuser")
    
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["refresh_token"] == refresh_token
    
    access_payload = TokenService.get_access_payload(data["access_token"])
    assert access_payload["sub"] == "refreshuser"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid_refresh_token"
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_protected_route_access(client, create_test_user):
    response = await client.get("/api/v1/test-protected")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    user = await create_test_user(username="authorizeduser", password="password")
    access_token = TokenService.create_access_token(user.username)
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/test-protected", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "authorizeduser"
    assert data["id"] == user.id


@pytest.mark.asyncio
async def test_get_current_user_dependency_cases(db_session, create_test_user):
    user = await create_test_user(username="depuser", password="password")
    
    access_token = TokenService.create_access_token(user.username)
    current_user = await get_current_user(token=access_token, db=db_session)
    assert current_user.id == user.id
    assert current_user.username == user.username
    
    refresh_token = TokenService.create_refresh_token(user.username)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=refresh_token, db=db_session)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail in ("Invalid token type", "Invalid token")
    
    deleted_token = TokenService.create_access_token("deleteduser")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=deleted_token, db=db_session)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "User not found"
