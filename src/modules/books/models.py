import enum
from sqlalchemy import Table, Column, ForeignKey, Integer, String, Enum, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True)
)


class GenreEnum(str, enum.Enum):
    FICTION = "Fiction"
    NON_FICTION = "Non-Fiction"
    MYSTERY = "Mystery"
    SCI_FI = "Science Fiction"
    FANTASY = "Fantasy"
    BIOGRAPHY = "Biography"
    HISTORY = "History"


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    books: Mapped[list["Book"]] = relationship(
        secondary=book_authors,
        back_populates="authors",
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="check_author_name_non_empty"),
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[GenreEnum] = mapped_column(Enum(GenreEnum), nullable=False)
    publication_year: Mapped[int] = mapped_column(nullable=False)

    authors: Mapped[list[Author]] = relationship(
        secondary=book_authors,
        back_populates="books",
    )

    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="check_book_title_non_empty"),
        CheckConstraint("publication_year >= 1800 AND publication_year <= 2026", name="check_publication_year_range"),
    )
