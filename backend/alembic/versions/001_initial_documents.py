"""Initial migration: create documents table

Revision ID: 001_initial_documents
Revises: 
Create Date: 2026-10-01 22:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_documents'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('department', sa.String(length=100), nullable=False, server_default='General'),
        sa.Column('owner', sa.String(length=100), nullable=False, server_default='System'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='uploaded'),
        sa.Column('version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_id', 'documents', ['id'], unique=False)
    op.create_index('ix_documents_filename', 'documents', ['filename'], unique=False)
    op.create_index('ix_documents_file_type', 'documents', ['file_type'], unique=False)
    op.create_index('ix_documents_department', 'documents', ['department'], unique=False)
    op.create_index('ix_documents_status', 'documents', ['status'], unique=False)
    op.create_index('ix_documents_created_at', 'documents', ['created_at'], unique=False)
    op.create_index('idx_doc_dept_status', 'documents', ['department', 'status'], unique=False)
    op.create_index('idx_doc_type_status', 'documents', ['file_type', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_doc_type_status', table_name='documents')
    op.drop_index('idx_doc_dept_status', table_name='documents')
    op.drop_index('ix_documents_created_at', table_name='documents')
    op.drop_index('ix_documents_status', table_name='documents')
    op.drop_index('ix_documents_department', table_name='documents')
    op.drop_index('ix_documents_file_type', table_name='documents')
    op.drop_index('ix_documents_filename', table_name='documents')
    op.drop_index('ix_documents_id', table_name='documents')
    op.drop_table('documents')
