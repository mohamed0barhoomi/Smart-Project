from django import forms

from .models import Projet


class ProjetForm(forms.ModelForm):
    class Meta:
        model = Projet
        fields = ["nom", "description"]
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Ex : Application de gestion de bibliothèque"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "En une ou deux phrases, à quoi sert ce projet ?"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        # On reçoit l'utilisateur connecté (envoyé par la vue) pour vérifier
        # l'unicité du nom parmi SES projets.
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_nom(self):
        nom = self.cleaned_data["nom"].strip()
        doublons = Projet.objects.filter(proprietaire=self.user, nom__iexact=nom)
        if self.instance.pk:                      # en modification : ignorer le projet lui-même
            doublons = doublons.exclude(pk=self.instance.pk)
        if doublons.exists():
            raise forms.ValidationError("Vous avez déjà un projet avec ce nom.")
        return nom
