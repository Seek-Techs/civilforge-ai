from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Project(models.Model):

    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    location = models.CharField(max_length=255, blank=True, help_text="Site location (city/state)")
    notes = models.TextField(blank=True, help_text="Internal notes or comments")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)  # fixed typo: was update_at
    boq_result = models.JSONField(null=True, blank=True)
    boq_generated_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and hasattr(self, '_request_user') and self._request_user:
            self.owner = self._request_user
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def boq_grand_total(self):
        if self.boq_result:
            return self.boq_result.get('grand_total_naira', 0)
        return None

    @property
    def status_badge_class(self):
        return {
            'planning': 'bg-secondary',
            'active': 'bg-success',
            'on_hold': 'bg-warning text-dark',
            'completed': 'bg-primary',
        }.get(self.status, 'bg-secondary')

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Projects"
