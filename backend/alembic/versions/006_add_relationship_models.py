"""Add EntityRelationship model and relationship extraction fields on Document

Revision ID: 006_add_relationship_models
Revises: 005_add_entity_models
Create Date: 2026-10-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_relationship_models'
down_revision: Union[str, None] = '005_add_entity_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Create entity_relationships table                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        'entity_relationships',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('source_entity_id', sa.String(36), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_entity_id', sa.String(36), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relationship_type', sa.String(100), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('evidence_text', sa.Text(), nullable=True),
        sa.Column('chunk_id', sa.String(36), sa.ForeignKey('document_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_start_char', sa.Integer(), nullable=True),
        sa.Column('source_end_char', sa.Integer(), nullable=True),
        sa.Column('target_start_char', sa.Integer(), nullable=True),
        sa.Column('target_end_char', sa.Integer(), nullable=True),
        sa.Column('extra_metadata', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True, index=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            'source_entity_id',
            'target_entity_id',
            'relationship_type',
            'chunk_id',
            name='uq_entity_rel_source_target_type_chunk',
        ),
    )
    op.create_index('idx_rel_source_entity', 'entity_relationships', ['source_entity_id'])
    op.create_index('idx_rel_target_entity', 'entity_relationships', ['target_entity_id'])
    op.create_index('idx_rel_type', 'entity_relationships', ['relationship_type'])
    op.create_index('idx_rel_chunk', 'entity_relationships', ['chunk_id'])
    op.create_index('idx_rel_document', 'entity_relationships', ['document_id'])
    op.create_index('idx_rel_confidence', 'entity_relationships', ['confidence'])
    op.create_index('idx_rel_hash_provider', 'entity_relationships', ['content_hash', 'provider', 'model'])

    # ------------------------------------------------------------------ #
    # 2. Add relationship extraction tracking columns to documents        #
    # ------------------------------------------------------------------ #
    op.add_column('documents', sa.Column(
        'relationship_extraction_status', sa.String(50), nullable=False, server_default='not_started'
    ))
    op.add_column('documents', sa.Column(
        'relationship_count', sa.Integer(), nullable=False, server_default='0'
    ))
    op.create_index('idx_doc_rel_status', 'documents', ['relationship_extraction_status'])


def downgrade() -> None:
    op.drop_index('idx_doc_rel_status', table_name='documents')
    op.drop_column('documents', 'relationship_count')
    op.drop_column('documents', 'relationship_extraction_status')

    op.drop_index('idx_rel_hash_provider', table_name='entity_relationships')
    op.drop_index('idx_rel_confidence', table_name='entity_relationships')
    op.drop_index('idx_rel_document', table_name='entity_relationships')
    op.drop_index('idx_rel_chunk', table_name='entity_relationships')
    op.drop_index('idx_rel_type', table_name='entity_relationships')
    op.drop_index('idx_rel_target_entity', table_name='entity_relationships')
    op.drop_index('idx_rel_source_entity', table_name='entity_relationships')
    op.drop_table('entity_relationships')
