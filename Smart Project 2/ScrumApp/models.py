from django.db import models

from ProjectsApp.models import Project
from UsersApp.models import TimeStampedModel, User


class ScrumWorkspace(TimeStampedModel):
    class TaskStatus(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    backlog = models.JSONField(default=list, blank=True)
    sprints = models.JSONField(default=list, blank=True)
    tasks = models.JSONField(default=list, blank=True)  # statut : TaskStatus
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="scrum_workspace",
    )

    def __str__(self):
        return f"Workspace : {self.project.title}"


class TaskComment(TimeStampedModel):
    task_id = models.CharField(max_length=50)
    content = models.TextField()
    workspace = models.ForeignKey(
        ScrumWorkspace,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="task_comments",
    )

    def __str__(self):
        return f"Commentaire de {self.user.email} sur {self.task_id}"
