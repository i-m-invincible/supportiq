"""Create ticket, policy, and audit tables."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('tickets',
        sa.Column('id', sa.String(30), primary_key=True),
        sa.Column('customer_name', sa.String(100), nullable=False),
        sa.Column('subject', sa.String(180), nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('assignee', sa.String(100), nullable=False),
        sa.Column('category', sa.String(40), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('sentiment', sa.String(20), nullable=False),
        sa.Column('analysis', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('draft_text', sa.Text, nullable=True),
        sa.Column('draft_meta', sa.JSON, nullable=True),
        sa.Column('approved_by', sa.String(100), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer, nullable=False),
    )
    for field in ['status', 'category', 'priority', 'created_at']:
        op.create_index(f'ix_tickets_{field}', 'tickets', [field])
    op.create_table('policies',
        sa.Column('id', sa.String(40), primary_key=True),
        sa.Column('title', sa.String(180), nullable=False),
        sa.Column('category', sa.String(40), nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('source', sa.String(240), nullable=False),
        sa.Column('active', sa.Boolean, nullable=False),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_policies_category', 'policies', ['category'])
    op.create_table('audit_events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('ticket_id', sa.String(30), sa.ForeignKey('tickets.id'), nullable=False),
        sa.Column('action', sa.String(60), nullable=False),
        sa.Column('actor', sa.String(100), nullable=False),
        sa.Column('details', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_events_ticket_id', 'audit_events', ['ticket_id'])


def downgrade():
    op.drop_table('audit_events')
    op.drop_table('policies')
    op.drop_table('tickets')
