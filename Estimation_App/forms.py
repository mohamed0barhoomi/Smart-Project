from django import forms

from .models import Estimation


class EstimationForm(forms.ModelForm):
    """Formulaire de modification (la création est faite par l'IA)."""

    class Meta:
        model = Estimation
        fields = ["resume", "cout", "delai", "hypotheses"]
        widgets = {
            "resume": forms.Textarea(attrs={"rows": 5}),
            "cout": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "delai": forms.NumberInput(attrs={"step": "0.5", "min": "0"}),
            "hypotheses": forms.Textarea(attrs={"rows": 4}),
        }
