from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class TimeStampedModel(models.Model):
    """Classe abstraite : created_at et updated_at pour tous les modèles."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, role=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        if role is None:
            raise ValueError(
                "Le rôle doit être fourni selon le contexte d'inscription."
            )
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields["role"] = User.UserRole.ADMIN
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, TimeStampedModel):
    class UserRole(models.TextChoices):
        USER = "user", "User"
        COMPANY = "company", "Company"
        ADMIN = "admin", "Admin"

    username = None  # l'email sert d'identifiant de connexion
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20, choices=UserRole.choices, default=UserRole.USER
    )
    company_name = models.CharField(max_length=150, blank=True)
    company_description = models.TextField(blank=True)
    company_skills = models.JSONField(default=list, blank=True)
    # first_name et last_name hérités d'AbstractUser

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
