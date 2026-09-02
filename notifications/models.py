from django.conf import settings
from django.db import models


class NotificationCategory(models.TextChoices):
    INJURY = 'injury', 'Player injury'
    SUSPENSION = 'suspension', 'Player suspension'
    LINEUP = 'lineup', 'Starting lineup announcement'
    STATUS_CHANGE = 'status_change', 'Major status change'
    NEWS = 'news', 'Important news'
    PRICE_CHANGE = 'price_change', 'Player price change'
    AUCTION_REMINDER = 'auction_reminder', 'Auction reminder'
    AVAILABILITY_CHANGE = 'availability_change', 'Player availability change'


class NotificationPreference(models.Model):
    """Per-user, per-category opt-in. Notifications are configurable per
    user (see AGENTS.md > Notifications) — this is deliberately a thin
    scaffold; delivery channels/scheduling are a future feature."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    category = models.CharField(max_length=25, choices=NotificationCategory.choices)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'category'], name='unique_preference_per_user_category'),
        ]

    def __str__(self):
        return f"{self.user} — {self.get_category_display()}: {'on' if self.is_enabled else 'off'}"


class Notification(models.Model):
    """A single notification instance delivered (or queued) for a user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    category = models.CharField(max_length=25, choices=NotificationCategory.choices)
    message = models.CharField(max_length=300)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message
