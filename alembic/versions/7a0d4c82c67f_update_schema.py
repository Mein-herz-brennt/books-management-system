"""update_schema

Revision ID: 7a0d4c82c67f
Revises: 9e92ed67f4c0
Create Date: 2026-05-22 18:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a0d4c82c67f'
down_revision: Union[str, Sequence[str], None] = '9e92ed67f4c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add created_at column to users table
    op.add_column('users', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))

    # 1.1 Create revoked_tokens table
    op.create_table('revoked_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )

    # 2. Modify check constraints on books table (replace length with char_length, and remove upper limit on year)
    # We drop the old check constraints and recreate them using char_length
    try:
        op.drop_constraint('check_book_title_non_empty', 'books', type_='check')
    except Exception:
        pass
    try:
        op.drop_constraint('check_publication_year_range', 'books', type_='check')
    except Exception:
        pass

    op.create_check_constraint(
        'check_book_title_non_empty',
        'books',
        'char_length(trim(title)) > 0'
    )
    op.create_check_constraint(
        'check_publication_year_range',
        'books',
        'publication_year >= 1800'
    )

    # 3. Modify check constraints on authors table (replace length with char_length)
    try:
        op.drop_constraint('check_author_name_non_empty', 'authors', type_='check')
    except Exception:
        pass

    op.create_check_constraint(
        'check_author_name_non_empty',
        'authors',
        'char_length(trim(name)) > 0'
    )


def downgrade() -> None:
    # 1. Revert check constraints on authors table
    try:
        op.drop_constraint('check_author_name_non_empty', 'authors', type_='check')
    except Exception:
        pass
    op.create_check_constraint(
        'check_author_name_non_empty',
        'authors',
        'length(trim(name)) > 0'
    )

    # 2. Revert check constraints on books table
    try:
        op.drop_constraint('check_book_title_non_empty', 'books', type_='check')
    except Exception:
        pass
    try:
        op.drop_constraint('check_publication_year_range', 'books', type_='check')
    except Exception:
        pass

    op.create_check_constraint(
        'check_book_title_non_empty',
        'books',
        'length(trim(title)) > 0'
    )
    op.create_check_constraint(
        'check_publication_year_range',
        'books',
        'publication_year >= 1800 AND publication_year <= 2026'
    )

    # 3. Drop created_at column from users table
    op.drop_column('users', 'created_at')

    # 4. Drop revoked_tokens table
    op.drop_table('revoked_tokens')
