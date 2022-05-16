"""init_table

Revision ID: 97fbf53bbc03
Revises: 54a2a03ba7a8
Create Date: 2022-05-16 10:05:07.784638

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '97fbf53bbc03'
down_revision = '54a2a03ba7a8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ip_proxy',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('ip', sa.String(length=255), nullable=True),
                    sa.Column('protocol', sa.String(length=6), nullable=True, comment='代理 IP 的 schema'),
                    sa.Column('port', sa.Integer(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('scene_proxy',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('proxy_id', sa.Integer(), nullable=True),
                    sa.Column('name', sa.String(length=255), nullable=True),
                    sa.Column('alive_count', sa.Integer(), nullable=True, comment='存活计数。可用加一，不可用减一'),
                    sa.Column('update_time', sa.DateTime(), nullable=True, comment='最近一次更新时间'),
                    sa.ForeignKeyConstraint(['proxy_id'], ['ip_proxy.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('scene_proxy')
    op.drop_table('ip_proxy')
    # ### end Alembic commands ###