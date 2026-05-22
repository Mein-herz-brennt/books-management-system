from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from src.modules.auth.service import jwt_token
from src.modules.users.models import User, RevokedToken
from sqlalchemy import select
from src.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: AsyncSession = Depends(get_db)) -> User | None:
    blacklisted = await db.execute(select(RevokedToken).where(RevokedToken.token == token))
    if blacklisted.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    payload = jwt_token.get_access_payload(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token payload')

    token_type = payload.get("type")
    if not token_type or token_type != 'access':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user