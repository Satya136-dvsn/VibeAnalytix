"""Initial schema setup with all 7 tables and pgvector support.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-04-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_ref', sa.String(1024), nullable=False),
        sa.Column('status', sa.String(50), server_default='queued', nullable=False),
        sa.Column('current_stage', sa.String(255), nullable=True),
        sa.Column('progress_pct', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint("source_type IN ('github', 'zip')", name='valid_source_type'),
        sa.CheckConstraint("status IN ('queued', 'in_progress', 'completed', 'failed')", name='valid_status'),
        sa.CheckConstraint('progress_pct >= 0 AND progress_pct <= 100', name='valid_progress'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create parsed_files table
    op.create_table(
        'parsed_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('language', sa.String(100), nullable=True),
        sa.Column('parse_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create function_summaries table with pgvector support
    op.create_table(
        'function_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('function_name', sa.String(255), nullable=False),
        sa.Column('line_start', sa.Integer(), nullable=True),
        sa.Column('line_end', sa.Integer(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('embedding', sa.text('vector(1536)'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    # Create pgvector index for semantic search using IVFFlat
    op.execute("""
        CREATE INDEX idx_function_summaries_embedding 
        ON function_summaries USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    
    # Create file_summaries table
    op.create_table(
        'file_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create module_summaries table
    op.create_table(
        'module_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('module_path', sa.String(1024), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create project_results table with JSONB support
    op.create_table(
        'project_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_summary', sa.Text(), nullable=True),
        sa.Column('overview_explanation', sa.Text(), nullable=True),
        sa.Column('flow_explanation', sa.Text(), nullable=True),
        sa.Column('dependency_graph', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('entry_points', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('circular_deps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('external_deps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('file_tree', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('per_file_explanations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('project_results')
    op.drop_table('module_summaries')
    op.drop_table('file_summaries')
    op.drop_table('function_summaries')
    op.drop_table('parsed_files')
    op.drop_table('jobs')
    op.drop_table('users')
    
    # Drop pgvector extension
    op.execute('DROP EXTENSION IF EXISTS "vector"')
