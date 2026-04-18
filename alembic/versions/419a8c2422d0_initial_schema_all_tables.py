"""initial_schema_all_tables

Revision ID: 419a8c2422d0
Revises:
Create Date: 2026-04-18 17:56:11.546824

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '419a8c2422d0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chatsession',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'joblisting',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('company_name', sa.Text(), nullable=False),
        sa.Column('location', sa.Text(), nullable=False),
        sa.Column('apply_url', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('posted_date', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'searchhistory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_query', sa.Text(), nullable=False),
        sa.Column('resume_name', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'chatmessage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chatsession.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chatmessage_role'), 'chatmessage', ['role'], unique=False)
    op.create_index(op.f('ix_chatmessage_session_id'), 'chatmessage', ['session_id'], unique=False)

    op.create_table(
        'jobanalysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('skills', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('similarity_score', sa.Integer(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['joblisting.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('jobanalysis')
    op.drop_index(op.f('ix_chatmessage_session_id'), table_name='chatmessage')
    op.drop_index(op.f('ix_chatmessage_role'), table_name='chatmessage')
    op.drop_table('chatmessage')
    op.drop_table('searchhistory')
    op.drop_table('joblisting')
    op.drop_table('chatsession')
