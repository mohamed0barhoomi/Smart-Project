from django import forms

from .models import Besoin


class BesoinForm(forms.ModelForm):
    class Meta:
        model = Besoin
        fields = ["type_besoin", "titre", "description", "priorite", "categorie"]
        widgets = {
            "titre": forms.TextInput(attrs={"placeholder": "Ex : L'utilisateur peut s'authentifier"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        # clean() sert à valider plusieurs champs ensemble
        donnees = super().clean()
        type_besoin = donnees.get("type_besoin")
        categorie = donnees.get("categorie")

        if type_besoin == "NF" and not categorie:
            self.add_error("categorie", "Choisissez une catégorie pour un besoin non fonctionnel.")
        if type_besoin == "F":
            donnees["categorie"] = ""      # pas de catégorie pour un besoin fonctionnel
        return donnees
