"""Bootstrap schema from SQLAlchemy models (baseline migration).

Revision ID: 20250512_0001
Revises:
Create Date: 2025-05-12

Subsequent revisions should use op.add_column / op.create_table as needed.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20250512_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    from models import Base

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from models import Base

    Base.metadata.drop_all(bind=bind)
