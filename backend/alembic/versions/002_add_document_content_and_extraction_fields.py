"""Add DocumentContent model and extraction fields to documents table

Revision ID: 002_extraction_and_content
Revises: 001_initial_documents
Create Date: 2026-10-01 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_extraction_and_content'
down_revision: Union[str, None] = '001_initial_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add extraction & storage columns to documents table
    op.add_column('documents', sa.Column('storage_path', sa.String(length=512), nullable=True))
    op.add_column('documents', sa.Column('mime_type', sa.String(length=100), nullable=True))
    op.add_column('documents', sa.Column('extraction_status', sa.String(length=50), nullable=False, server_default='pending'))
    op.add_column('documents', sa.Column('extracted_text_length', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('documents', sa.Column('processing_error', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))

    op.create_index('idx_doc_extract_status', 'documents', ['extraction_status'], unique=False)

    # 2. Create document_contents table
    op.create_table(
        'document_contents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('character_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id')
    )
    op.create_index('ix_document_contents_id', 'document_contents', ['id'], unique=False)
    op.create_index('ix_document_contents_document_id', 'document_contents', ['document_id'], unique=True)


def downgrade() -> None:
    # 1. Drop document_contents table
    op.drop_index('ix_document_contents_document_id', table_name='document_contents')
    op.drop_index('ix_document_contents_id', table_name='document_contents')
    op.drop_table('document_contents')

    # 2. Drop columns and index from documents
    op.drop_index('idx_doc_extract_status', table_name='documents')
    op.drop_column('documents', 'processed_at')
    op.drop_column('documents', 'processing_error')
    op.drop_column('documents', 'extracted_text_length')
    op.drop_column('documents', 'extraction_status')
    op.drop_column('documents', 'mime_type')
    op.drop_column('documents', 'storage_path')
