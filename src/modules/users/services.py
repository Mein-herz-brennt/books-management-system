from fastapi import Depends, HTTPException, status
from src.core.security import verify_password, get_password_hash
from src.modules.users.models import User
from src.modules.users.schemas import RegisterRequest
from src.modules.users.repositories import UserRepository


class UserService:
    def __init__(self, user_repo: UserRepository = Depends(UserRepository)):
        self.user_repo = user_repo

    async def create_user(self, data: RegisterRequest) -> User:
        if await self.user_repo.get_by_username(data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        new_user = User(
            username=data.username,
            password=get_password_hash(data.password),
        )
        return await self.user_repo.create(new_user)

    async def get_user_by_username(self, username: str) -> User | None:
        return await self.user_repo.get_by_username(username)

    async def authenticate_user(self, username: str, password: str) -> User | None:
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        return user