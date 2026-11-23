from django.db import models

from Projet_App.models import Projet


class Message(models.Model):
    """Un message du chat d'un projet (écrit par l'utilisateur ou par l'IA)."""

    ROLE_CHOICES = [
        ("user", "Utilisateur"),
        ("assistant", "Assistant"),
    ]

    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    contenu = models.TextField()
    # Nom du modèle Groq qui a répondu (utile pour montrer le fallback)
    modele = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.role} : {self.contenu[:40]}"
