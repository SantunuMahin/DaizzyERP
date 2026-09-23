"""
Enterprise immutable audit trail model.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class AuditLog(models.Model):
    """
    Immutable ledger of critical operational business events.
    Logs who, what, when, which entity, and contextual metadata.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100, db_index=True)
    entity = models.CharField(max_length=100, db_index=True)
    entity_id = models.BigIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity', 'entity_id']),
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"{self.created_at:%Y-%m-%d %H:%M} | {user_str} | {self.action} on {self.entity} #{self.entity_id}"
