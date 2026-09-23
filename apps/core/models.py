"""
Core abstract models and base definitions.
"""
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating
    created_at and updated_at fields.
    """
    created_at = models.DateTimeField(default=timezone.now, db_index=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class ActiveManager(models.Manager):
    """Manager returning only active objects."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class SoftDeleteModel(TimeStampedModel):
    """
    Abstract base model supporting soft deletion via an is_active flag.
    Historical business records should not be destructively deleted.
    """
    is_active = models.BooleanField(default=True, db_index=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark record as inactive."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def restore(self):
        """Restore soft-deleted record."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])
