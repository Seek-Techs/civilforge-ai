from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Project(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    update_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # If this is a new project (no pk yet) and request user is available
        if not self.pk and hasattr(self, '_request_user') and self._request_user:
            self.owner = self._request_user
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Projects"