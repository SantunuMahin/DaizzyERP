"""
Audit service helper.
"""
from .models import AuditLog


class AuditService:
    @staticmethod
    def log(action: str, entity: str, entity_id: int = None, user=None,
            metadata: dict = None, ip_address: str = None) -> AuditLog:
        """Create an immutable audit log entry."""
        return AuditLog.objects.create(
            action=action,
            entity=entity,
            entity_id=entity_id,
            user=user if getattr(user, 'is_authenticated', False) else None,
            metadata=metadata or {},
            ip_address=ip_address,
        )
