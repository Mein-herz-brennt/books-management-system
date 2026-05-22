from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, status, Depends
from jwt import ExpiredSignatureError, InvalidTokenError
from src.core.config import settings
from src.modules.users.services import UserService
from src.modules.auth.schemas import Token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.core.database import get_db
from src.modules.users.models import RevokedToken


class TokenService:

    @staticmethod
    def _create_token(data: dict, expires_delta: timedelta, secret: str) -> str:
        to_encode = data.copy()
        to_encode.update({'exp': datetime.now(timezone.utc) + expires_delta})
        return jwt.encode(payload=to_encode, key=secret, algorithm=settings.token.algorithm)

    @classmethod
    def create_access_token(cls, username: str) -> str:
        return cls._create_token(
            data={"sub": username, "type": "access"},
            expires_delta=timedelta(minutes=settings.token.access_time_to_expire),
            secret=settings.token.ACCESS_SECRET_KEY.get_secret_value()
        )

    @classmethod
    def create_refresh_token(cls, username: str) -> str:
        return cls._create_token(
            data={"sub": username, "type": "refresh"},
            expires_delta=timedelta(days=settings.token.refresh_time_to_expire),
            secret=settings.token.REFRESH_SECRET_KEY.get_secret_value()
        )

    @staticmethod
    def get_access_payload(token: str) -> dict:
        try:
            data = jwt.decode(token, settings.token.ACCESS_SECRET_KEY.get_secret_value(), algorithms=[settings.token.algorithm])
        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return data

    @staticmethod
    def get_refresh_payload(token: str) -> dict:
        try:
            data = jwt.decode(token, settings.token.REFRESH_SECRET_KEY.get_secret_value(), algorithms=[settings.token.algorithm])
        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        return data



class AuthService:
    def __init__(
            self,
            user_service: UserService = Depends(UserService),
            token_service: TokenService = Depends(lambda: jwt_token),
            db: AsyncSession = Depends(get_db)
    ):
        self.user_service = user_service
        self.token_service = token_service
        self.db = db

    async def login(self, username: str, password: str) -> Token:
        user = await self.user_service.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        return Token(
            access_token=self.token_service.create_access_token(user.username),
            refresh_token=self.token_service.create_refresh_token(user.username)
        )

    async def refresh(self, refresh_token: str) -> Token:
        blacklisted = await self.db.execute(select(RevokedToken).where(RevokedToken.token == refresh_token))
        if blacklisted.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

        payload = self.token_service.get_refresh_payload(refresh_token)
        username = payload.get("sub")
        token_type = payload.get("type")
        exp = payload.get("exp")

        if not username or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        await self._revoke_token(exp, refresh_token)

        return Token(
            access_token=self.token_service.create_access_token(username),
            refresh_token=self.token_service.create_refresh_token(username)
        )

    async def logout(self, access_token: str) -> None:
        payload = self.token_service.get_access_payload(access_token)
        exp = payload.get("exp")
        await self._revoke_token(exp, token=access_token)

    async def _revoke_token(self, exp, token: str) -> None:
        expires_at = datetime.now(timezone.utc)
        if exp:
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)

        revoked = RevokedToken(token=token, expires_at=expires_at)
        self.db.add(revoked)
        await self.db.commit()



jwt_token = TokenService()