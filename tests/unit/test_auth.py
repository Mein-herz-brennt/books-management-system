import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, status
from src.core.config import settings
from src.modules.auth.schemas import Token, RefreshTokenRequest
from src.modules.auth.service import TokenService, AuthService
from src.modules.users.models import User


def test_create_access_token():
    username = "testuser"
    token = TokenService.create_access_token(username)
    assert isinstance(token, str)
    
    payload = jwt.decode(
        token, 
        settings.token.ACCESS_SECRET_KEY.get_secret_value(), 
        algorithms=[settings.token.algorithm]
    )
    assert payload["sub"] == username
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token():
    username = "testuser"
    token = TokenService.create_refresh_token(username)
    assert isinstance(token, str)
    
    payload = jwt.decode(
        token, 
        settings.token.REFRESH_SECRET_KEY.get_secret_value(), 
        algorithms=[settings.token.algorithm]
    )
    assert payload["sub"] == username
    assert payload["type"] == "refresh"
    assert "exp" in payload


def test_get_access_payload_success():
    username = "testuser"
    token = TokenService.create_access_token(username)
    payload = TokenService.get_access_payload(token)
    assert payload["sub"] == username
    assert payload["type"] == "access"


def test_get_access_payload_invalid():
    with pytest.raises(HTTPException) as exc_info:
        TokenService.get_access_payload("invalid-token")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid token"


def test_get_access_payload_expired(monkeypatch):
    username = "testuser"
    past_exp = datetime.utcnow() - timedelta(minutes=5)
    expired_token = jwt.encode(
        {"sub": username, "type": "access", "exp": past_exp},
        settings.token.ACCESS_SECRET_KEY.get_secret_value(),
        algorithm=settings.token.algorithm
    )
    
    with pytest.raises(HTTPException) as exc_info:
        TokenService.get_access_payload(expired_token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Token has expired"


def test_get_refresh_payload_success():
    username = "testuser"
    token = TokenService.create_refresh_token(username)
    payload = TokenService.get_refresh_payload(token)
    assert payload["sub"] == username
    assert payload["type"] == "refresh"


def test_get_refresh_payload_invalid():
    with pytest.raises(HTTPException) as exc_info:
        TokenService.get_refresh_payload("invalid-token")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid refresh token"


def test_get_refresh_payload_expired():
    username = "testuser"
    past_exp = datetime.utcnow() - timedelta(days=1)
    expired_token = jwt.encode(
        {"sub": username, "type": "refresh", "exp": past_exp},
        settings.token.REFRESH_SECRET_KEY.get_secret_value(),
        algorithm=settings.token.algorithm
    )
    
    with pytest.raises(HTTPException) as exc_info:
        TokenService.get_refresh_payload(expired_token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Refresh token has expired"


@pytest.mark.asyncio
async def test_auth_service_login_success():
    mock_user = User(id=1, username="testuser", password="hashedpassword")
    
    mock_user_service = AsyncMock()
    mock_user_service.authenticate_user.return_value = mock_user
    
    mock_token_service = MagicMock()
    mock_token_service.create_access_token.return_value = "access_token_mock"
    mock_token_service.create_refresh_token.return_value = "refresh_token_mock"
    mock_db = AsyncMock()
    
    auth_service = AuthService(user_service=mock_user_service, token_service=mock_token_service, db=mock_db)
    
    result = await auth_service.login("testuser", "correctpassword")
    
    assert isinstance(result, Token)
    assert result.access_token == "access_token_mock"
    assert result.refresh_token == "refresh_token_mock"
    mock_user_service.authenticate_user.assert_called_once_with("testuser", "correctpassword")
    mock_token_service.create_access_token.assert_called_once_with("testuser")
    mock_token_service.create_refresh_token.assert_called_once_with("testuser")


@pytest.mark.asyncio
async def test_auth_service_login_failure():
    mock_user_service = AsyncMock()
    mock_user_service.authenticate_user.return_value = None
    
    mock_token_service = MagicMock()
    mock_db = AsyncMock()
    
    auth_service = AuthService(user_service=mock_user_service, token_service=mock_token_service, db=mock_db)
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.login("testuser", "wrongpassword")
        
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Incorrect username or password"
    mock_user_service.authenticate_user.assert_called_once_with("testuser", "wrongpassword")
    mock_token_service.create_access_token.assert_not_called()


@pytest.mark.asyncio
async def test_auth_service_refresh_success():
    mock_user_service = AsyncMock()
    
    mock_token_service = MagicMock()
    mock_token_service.get_refresh_payload.return_value = {"sub": "testuser", "type": "refresh"}
    mock_token_service.create_access_token.return_value = "new_access_token"
    mock_token_service.create_refresh_token.return_value = "new_refresh_token"
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    auth_service = AuthService(user_service=mock_user_service, token_service=mock_token_service, db=mock_db)
    
    result = await auth_service.refresh("old_refresh_token")
    
    assert isinstance(result, Token)
    assert result.access_token == "new_access_token"
    assert result.refresh_token == "new_refresh_token"
    mock_token_service.get_refresh_payload.assert_called_once_with("old_refresh_token")
    mock_token_service.create_access_token.assert_called_once_with("testuser")
    mock_token_service.create_refresh_token.assert_called_once_with("testuser")


@pytest.mark.asyncio
async def test_auth_service_refresh_invalid_token_type():
    mock_user_service = AsyncMock()
    
    mock_token_service = MagicMock()
    mock_token_service.get_refresh_payload.return_value = {"sub": "testuser", "type": "access"}
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    auth_service = AuthService(user_service=mock_user_service, token_service=mock_token_service, db=mock_db)
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh("invalid_refresh_token")
        
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid refresh token"
    mock_token_service.get_refresh_payload.assert_called_once_with("invalid_refresh_token")
    mock_token_service.create_access_token.assert_not_called()
