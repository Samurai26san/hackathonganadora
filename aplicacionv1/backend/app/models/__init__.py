"""Register all tables for Alembic and tests."""

from app.models.audit import AuditLog
from app.models.budget import (
    Area,
    Budget,
    BudgetModification,
    Cuenta,
    ExchangeRate,
    Financier,
    Gestion,
    ImportLog,
    Movement,
    Region,
    Rubro,
)
from app.models.dictionary import DataDictionary
from app.models.knowledge import KnowledgeChunk
from app.models.session import ChatMessage, ChatSession, ConversationContext
from app.models.user import AuthSession, OIDCTransaction, User

__all__ = [
    "AuditLog",
    "Area",
    "Budget",
    "BudgetModification",
    "Cuenta",
    "ExchangeRate",
    "Financier",
    "Gestion",
    "ImportLog",
    "Movement",
    "Region",
    "Rubro",
    "DataDictionary",
    "KnowledgeChunk",
    "ChatMessage",
    "ChatSession",
    "ConversationContext",
    "AuthSession",
    "OIDCTransaction",
    "User",
]

from app.models.accounting import (  # noqa: F401,E402
    CurationBatch,
    CurationRow,
    FinancialDisclosure,
    JournalEntry,
    JournalLine,
    LedgerAccount,
)
