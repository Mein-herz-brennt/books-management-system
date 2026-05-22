from datetime import datetime
from sqlalchemy import func, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from src.core.database import Base

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class RevokedToken(Base):
    __tablename__ = 'revoked_tokens'
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)