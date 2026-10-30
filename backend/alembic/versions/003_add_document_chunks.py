"""Add DocumentChunk model and total_chunks to documents table

Revision ID: 003_add_document_chunks
Revises: 002_extraction_and_content
Create Date: 2026-10-02 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_document_chunks'
down_revision: Union[str, None] = '002_extraction_and_content'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add total_chunks column to documents table
    op.add_column('documents', sa.Column('total_chunks', sa.Integer(), nullable=False, server_default='0'))

    # 2. Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('char_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_header', sa.String(length=255), nullable=True),
        sa.Column('chunk_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_document_chunks_id', 'document_chunks', ['id'], unique=False)
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'], unique=False)
    op.create_index('idx_chunk_doc_index', 'document_chunks', ['document_id', 'chunk_index'], unique=False)
    op.create_index('idx_chunk_doc_page', 'document_chunks', ['document_id', 'page_number'], unique=False)


def downgrade() -> None:
    # 1. Drop document_chunks table and indexes
    op.drop_index('idx_chunk_doc_page', table_name='document_chunks')
    op.drop_index('idx_chunk_doc_index', table_name='document_chunks')
    op.drop_index('ix_document_chunks_document_id', table_name='document_chunks')
    op.drop_index('ix_document_chunks_id', table_name='document_chunks')
    op.drop_table('document_chunks')

    # 2. Drop total_chunks column from documents
    op.drop_column('documents', 'total_chunks')
