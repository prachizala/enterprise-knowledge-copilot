"""Add Entity and ChunkEntity models, and entity extraction fields on Document

Revision ID: 005_add_entity_models
Revises: 004_add_vector_and_chunk_embeddings
Create Date: 2026-10-02 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_entity_models'
down_revision: Union[str, None] = '004_add_vector_and_chunk_embeddings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Create canonical entities table                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        'entities',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('canonical_name', sa.String(512), nullable=False),
        sa.Column('display_name', sa.String(512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('mention_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('entity_type', 'canonical_name', name='uq_entity_type_canonical'),
    )
    op.create_index('idx_entity_type', 'entities', ['entity_type'])
    op.create_index('idx_entity_canonical', 'entities', ['canonical_name'])
    op.create_index('idx_entity_type_canonical', 'entities', ['entity_type', 'canonical_name'])

    # ------------------------------------------------------------------ #
    # 2. Create chunk_entities mention-link table                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        'chunk_entities',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('chunk_id', sa.String(36), sa.ForeignKey('document_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_id', sa.String(36), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mention_text', sa.String(512), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('extra_metadata', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True, index=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('section_header', sa.String(255), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_chunk_entity_chunk', 'chunk_entities', ['chunk_id'])
    op.create_index('idx_chunk_entity_entity', 'chunk_entities', ['entity_id'])
    op.create_index('idx_chunk_entity_document', 'chunk_entities', ['document_id'])
    op.create_index('idx_chunk_entity_hash_provider', 'chunk_entities', ['content_hash', 'provider', 'model'])

    # ------------------------------------------------------------------ #
    # 3. Add entity extraction tracking columns to documents              #
    # ------------------------------------------------------------------ #
    op.add_column('documents', sa.Column(
        'entity_extraction_status', sa.String(50), nullable=False, server_default='not_started'
    ))
    op.add_column('documents', sa.Column(
        'entity_mention_count', sa.Integer(), nullable=False, server_default='0'
    ))
    op.add_column('documents', sa.Column(
        'unique_entity_count', sa.Integer(), nullable=False, server_default='0'
    ))
    op.create_index('idx_doc_entity_status', 'documents', ['entity_extraction_status'])


def downgrade() -> None:
    op.drop_index('idx_doc_entity_status', table_name='documents')
    op.drop_column('documents', 'unique_entity_count')
    op.drop_column('documents', 'entity_mention_count')
    op.drop_column('documents', 'entity_extraction_status')

    op.drop_index('idx_chunk_entity_hash_provider', table_name='chunk_entities')
    op.drop_index('idx_chunk_entity_document', table_name='chunk_entities')
    op.drop_index('idx_chunk_entity_entity', table_name='chunk_entities')
    op.drop_index('idx_chunk_entity_chunk', table_name='chunk_entities')
    op.drop_table('chunk_entities')

    op.drop_index('idx_entity_type_canonical', table_name='entities')
    op.drop_index('idx_entity_canonical', table_name='entities')
    op.drop_index('idx_entity_type', table_name='entities')
    op.drop_table('entities')
