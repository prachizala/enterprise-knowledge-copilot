"""Add pgvector extension, ChunkEmbedding model, and embedding metadata fields

Revision ID: 004_add_vector_and_chunk_embeddings
Revises: 003_add_document_chunks
Create Date: 2026-10-02 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '004_add_vector_and_chunk_embeddings'
down_revision: Union[str, None] = '003_add_document_chunks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension if running on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

    # 2. Add embedding status tracking columns to documents table
    op.add_column('documents', sa.Column('embedding_status', sa.String(length=50), nullable=False, server_default='not_started'))
    op.add_column('documents', sa.Column('embedded_chunks', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('documents', sa.Column('embedding_model', sa.String(length=100), nullable=True))
    op.create_index('idx_doc_embed_status', 'documents', ['embedding_status'], unique=False)

    # 3. Add content_hash column to document_chunks table
    op.add_column('document_chunks', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.create_index('idx_chunk_content_hash', 'document_chunks', ['content_hash'], unique=False)

    # 4. Create chunk_embeddings table
    op.create_table(
        'chunk_embeddings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('chunk_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False, server_default='text-embedding-3-small'),
        sa.Column('dimensions', sa.Integer(), nullable=False, server_default='1536'),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chunk_id', 'model', name='uq_chunk_model_embedding'),
    )
    op.create_index('ix_chunk_embeddings_id', 'chunk_embeddings', ['id'], unique=False)
    op.create_index('ix_chunk_embeddings_chunk_id', 'chunk_embeddings', ['chunk_id'], unique=False)
    op.create_index('ix_chunk_embeddings_document_id', 'chunk_embeddings', ['document_id'], unique=False)
    op.create_index('ix_chunk_embeddings_model', 'chunk_embeddings', ['model'], unique=False)
    op.create_index('idx_embedding_doc_model', 'chunk_embeddings', ['document_id', 'model'], unique=False)

    # 5. Create HNSW index for cosine distance on PostgreSQL
    if bind.dialect.name == 'postgresql':
        op.execute(
            'CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw '
            'ON chunk_embeddings USING hnsw (embedding vector_cosine_ops) '
            'WITH (m = 16, ef_construction = 64);'
        )


def downgrade() -> None:
    bind = op.get_bind()

    # 1. Drop chunk_embeddings table and indexes
    if bind.dialect.name == 'postgresql':
        op.execute('DROP INDEX IF EXISTS idx_chunk_embeddings_hnsw;')

    op.drop_index('idx_embedding_doc_model', table_name='chunk_embeddings')
    op.drop_index('ix_chunk_embeddings_model', table_name='chunk_embeddings')
    op.drop_index('ix_chunk_embeddings_document_id', table_name='chunk_embeddings')
    op.drop_index('ix_chunk_embeddings_chunk_id', table_name='chunk_embeddings')
    op.drop_index('ix_chunk_embeddings_id', table_name='chunk_embeddings')
    op.drop_table('chunk_embeddings')

    # 2. Drop content_hash from document_chunks
    op.drop_index('idx_chunk_content_hash', table_name='document_chunks')
    op.drop_column('document_chunks', 'content_hash')

    # 3. Drop embedding columns from documents
    op.drop_index('idx_doc_embed_status', table_name='documents')
    op.drop_column('documents', 'embedding_model')
    op.drop_column('documents', 'embedded_chunks')
    op.drop_column('documents', 'embedding_status')
