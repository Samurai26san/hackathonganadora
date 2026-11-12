"""Initial ExB schema with pgvector and HNSW index."""
from alembic import op
from app.core.database import Base
import app.models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(op.get_bind())


def downgrade():
    raise RuntimeError("Restaurar un respaldo explícito; el MVP no elimina datos financieros.")
