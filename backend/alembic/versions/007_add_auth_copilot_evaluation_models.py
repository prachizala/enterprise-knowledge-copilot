"""Add users, RBAC, conversations, citations, feedback, jobs, and evaluations

Revision ID: 007_add_auth_copilot_evaluation_models
Revises: 006_add_relationship_models
Create Date: 2026-10-02 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_add_auth_copilot_evaluation_models'
down_revision: Union[str, None] = '006_add_relationship_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add RBAC, deduplication, and sync columns to documents table
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('visibility', sa.String(50), nullable=False, server_default='organization'))
        batch_op.add_column(sa.Column('allowed_roles', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('allowed_users', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('content_hash', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('graph_sync_status', sa.String(50), nullable=False, server_default='pending'))
        batch_op.create_index('ix_documents_content_hash', ['content_hash'])

    # 2. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='EMPLOYEE'),
        sa.Column('department', sa.String(100), nullable=False, server_default='General'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_department', 'users', ['department'])

    # 3. Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False, server_default='New Enterprise Copilot Chat'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_conversations_id', 'conversations', ['id'])
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])

    # 4. Create conversation_messages table
    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('grounding_score', sa.Float(), nullable=True),
        sa.Column('query_category', sa.String(50), nullable=True),
        sa.Column('retrieval_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_conversation_messages_id', 'conversation_messages', ['id'])
    op.create_index('ix_conversation_messages_conversation_id', 'conversation_messages', ['conversation_id'])

    # 5. Create message_citations table
    op.create_table(
        'message_citations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('message_id', sa.String(36), sa.ForeignKey('conversation_messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('citation_index', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('document_name', sa.String(255), nullable=False),
        sa.Column('chunk_id', sa.String(36), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.Column('section_title', sa.String(255), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('evidence_type', sa.String(50), nullable=False, server_default='document_chunk'),
    )
    op.create_index('ix_message_citations_id', 'message_citations', ['id'])
    op.create_index('ix_message_citations_message_id', 'message_citations', ['message_id'])
    op.create_index('ix_message_citations_document_id', 'message_citations', ['document_id'])
    op.create_index('ix_message_citations_chunk_id', 'message_citations', ['chunk_id'])

    # 6. Create message_feedback table
    op.create_table(
        'message_feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('message_id', sa.String(36), sa.ForeignKey('conversation_messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('rating', sa.String(50), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_message_feedback_id', 'message_feedback', ['id'])
    op.create_index('ix_message_feedback_message_id', 'message_feedback', ['message_id'])
    op.create_index('ix_message_feedback_user_id', 'message_feedback', ['user_id'])

    # 7. Create processing_jobs table
    op.create_table(
        'processing_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False, server_default='full_pipeline'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('current_step', sa.String(50), nullable=False, server_default='uploaded'),
        sa.Column('progress_pct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_processing_jobs_id', 'processing_jobs', ['id'])
    op.create_index('ix_processing_jobs_document_id', 'processing_jobs', ['document_id'])
    op.create_index('ix_processing_jobs_status', 'processing_jobs', ['status'])

    # 8. Create evaluation_runs table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('total_queries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_recall', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('avg_precision', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('avg_groundedness', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('avg_citation_coverage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('hallucination_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('avg_latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_evaluation_runs_id', 'evaluation_runs', ['id'])

    # 9. Create evaluation_results table
    op.create_table(
        'evaluation_results',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('evaluation_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('actual_answer', sa.Text(), nullable=False),
        sa.Column('groundedness_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('citation_coverage', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_evaluation_results_id', 'evaluation_results', ['id'])
    op.create_index('ix_evaluation_results_run_id', 'evaluation_results', ['run_id'])


def downgrade() -> None:
    op.drop_table('evaluation_results')
    op.drop_table('evaluation_runs')
    op.drop_table('processing_jobs')
    op.drop_table('message_feedback')
    op.drop_table('message_citations')
    op.drop_table('conversation_messages')
    op.drop_table('conversations')
    op.drop_table('users')

    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_index('ix_documents_content_hash')
        batch_op.drop_column('graph_sync_status')
        batch_op.drop_column('content_hash')
        batch_op.drop_column('allowed_users')
        batch_op.drop_column('allowed_roles')
        batch_op.drop_column('visibility')
