from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class InscriptionForm(UserCreationForm):
    """Formulaire d'inscription : on reprend celui de Django et on ajoute l'email."""

    email = forms.EmailField(required=True, label="Adresse e-mail")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        # Validation personnalisée : un email ne peut servir qu'à un seul compte
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse.")
        return email
