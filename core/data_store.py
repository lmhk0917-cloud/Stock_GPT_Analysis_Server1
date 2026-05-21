"""Server-side data store facade.

This replaces direct personal-project DB coupling with provider-neutral audit
storage. Keep common market data separate from user-specific tables.
"""

from core.audit_store import AuditStore


__all__ = ["AuditStore"]
