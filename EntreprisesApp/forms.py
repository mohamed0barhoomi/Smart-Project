from django import forms

from .models import Entreprise


class EntrepriseForm(forms.ModelForm):
    class Meta:
        model = Entreprise
        fields = ["nom", "secteur", "competences", "localisation", "type_opportunite", "description", "site_web"]
        widgets = {
            "competences": forms.Textarea(attrs={"rows": 2}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "site_web": forms.URLInput(attrs={"placeholder": "https://exemple.com"}),
        }

    def clean_nom(self):
        # unique=True sur le modèle vérifie déjà le doublon, en excluant l'entreprise modifiée.
        return self.cleaned_data["nom"].strip()