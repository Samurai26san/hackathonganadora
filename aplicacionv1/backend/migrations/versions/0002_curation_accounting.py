"""Add isolated staging and double-entry ledger; preserve all existing facts."""

from alembic import op
from app.models.accounting import (
    CurationBatch,
    CurationRow,
    LedgerAccount,
    JournalEntry,
    JournalLine,
    FinancialDisclosure,
)

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    for model in (
        CurationBatch,
        CurationRow,
        LedgerAccount,
        JournalEntry,
        JournalLine,
        FinancialDisclosure,
    ):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError(
        "Restaurar respaldo explícito: no eliminar contabilidad ni trazabilidad."
    )
