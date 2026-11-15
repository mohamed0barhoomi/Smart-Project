from django.db import models

from UsersApp.models import TimeStampedModel, User


class Notification(TimeStampedModel):
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    def __str__(self):
        return f"Notification pour {self.user.email}"
