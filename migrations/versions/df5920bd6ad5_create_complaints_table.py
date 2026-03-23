"""create complaints and api_keys tables

Revision ID: df5920bd6ad5
Revises: bbab8035a8bf
Create Date: 2026-03-06 17:23:22.038601

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'df5920bd6ad5'
down_revision: Union[str, Sequence[str], None] = 'bbab8035a8bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # nyc_311_service_requests
    op.create_table(
        'nyc_311_service_requests',
        sa.Column('unique_key',                     sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_date',                   sa.DateTime(),   nullable=False),
        sa.Column('agency',                         sa.String(10),   nullable=False),
        sa.Column('agency_name',                    sa.String(255),  nullable=False),
        sa.Column('complaint_type',                 sa.String(255),  nullable=False),
        sa.Column('borough',                        sa.String(50),   nullable=False),
        sa.Column('status',                         sa.String(50),   nullable=False),
        sa.Column('closed_date',                    sa.DateTime(),   nullable=True),
        sa.Column('descriptor',                     sa.String(255),  nullable=True),
        sa.Column('location_type',                  sa.String(255),  nullable=True),
        sa.Column('incident_zip',                   sa.String(10),   nullable=True),
        sa.Column('city',                           sa.String(100),  nullable=True),
        sa.Column('resolution_description',         sa.Text(),       nullable=True),
        sa.Column('latitude',                       sa.Float(),      nullable=True),
        sa.Column('longitude',                      sa.Float(),      nullable=True),
        sa.Column('resolution_action_updated_date', sa.DateTime(),   nullable=True),
        sa.PrimaryKeyConstraint('unique_key'),
    )
    op.create_index(
        'idx_agency_borough_date',
        'nyc_311_service_requests',
        ['agency', 'borough', 'created_date']
    )

    # api_keys
    op.create_table(
        'api_keys',
        sa.Column('id',           sa.Integer(),                           nullable=False),
        sa.Column('key_prefix',   sa.String(8),                           nullable=False),
        sa.Column('key_hash',     sa.String(64),                          nullable=False),
        sa.Column('owner_id',     sa.Integer(),                           nullable=False),
        sa.Column('scopes',       postgresql.ARRAY(sa.String()),          nullable=False),
        sa.Column('created_at',   sa.DateTime(),                          nullable=False),
        sa.Column('expires_at',   sa.DateTime(),                          nullable=True),
        sa.Column('last_used_at', sa.DateTime(),                          nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['platform_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
    )
    op.create_index(op.f('ix_api_keys_id'),       'api_keys', ['id'],       unique=False)
    op.create_index(op.f('ix_api_keys_key_hash'),  'api_keys', ['key_hash'], unique=True)
    op.create_index(op.f('ix_api_keys_owner_id'),  'api_keys', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_api_keys_owner_id'),  table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key_hash'),  table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_id'),        table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index('idx_agency_borough_date',     table_name='nyc_311_service_requests')
    op.drop_table('nyc_311_service_requests')
