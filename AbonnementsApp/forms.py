import re
from datetime import date

from django import forms

from .models import SubscriptionPlan, UserSubscription


class PlanForm(forms.Form):
    name = forms.CharField(label="Nom", max_length=100)
    price = forms.DecimalField(label="Prix (DT)", max_digits=8, decimal_places=2, min_value=0)
    duration_days = forms.IntegerField(label="Durée (jours)", min_value=1)
    description = forms.CharField(label="Description", widget=forms.Textarea, required=False)
    is_active = forms.BooleanField(label="Proposé aux clients", required=False, initial=True)

    def __init__(self, *args, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.plan = plan

    def clean_name(self):
        name = self.cleaned_data['name']
        autres = SubscriptionPlan.objects.filter(name__iexact=name)
        if self.plan:
            autres = autres.exclude(pk=self.plan.pk)
        if autres.exists():
            raise forms.ValidationError("Un plan porte déjà ce nom.")
        return name


class PaiementForm(forms.Form):
    """Paiement simulé : les données de carte sont vérifiées puis oubliées, jamais enregistrées."""
    titulaire = forms.CharField(label="Titulaire de la carte", max_length=100)
    numero = forms.CharField(label="Numéro de carte", max_length=19,
                             widget=forms.TextInput(attrs={"placeholder": "4242 4242 4242 4242", "autocomplete": "off"}))
    expiration = forms.CharField(label="Expiration (MM/AA)", max_length=5,
                                 widget=forms.TextInput(attrs={"placeholder": "12/28", "autocomplete": "off"}))
    cvv = forms.CharField(label="CVV", max_length=3,
                          widget=forms.PasswordInput(attrs={"placeholder": "123", "autocomplete": "off"}))

    def clean_numero(self):
        numero = self.cleaned_data['numero'].replace(" ", "")
        if not re.fullmatch(r"\d{16}", numero):
            raise forms.ValidationError("Le numéro de carte doit contenir 16 chiffres.")
        return numero

    def clean_expiration(self):
        expiration = self.cleaned_data['expiration']
        if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", expiration):
            raise forms.ValidationError("Format attendu : MM/AA.")
        mois, annee = int(expiration[:2]), 2000 + int(expiration[3:])
        aujourd_hui = date.today()
        if (annee, mois) < (aujourd_hui.year, aujourd_hui.month):
            raise forms.ValidationError("Cette carte est expirée.")
        return expiration

    def clean_cvv(self):
        cvv = self.cleaned_data['cvv']
        if not re.fullmatch(r"\d{3}", cvv):
            raise forms.ValidationError("Le CVV doit contenir 3 chiffres.")
        return cvv


class AbonnementStatutForm(forms.Form):
    status = forms.ChoiceField(label="Statut", choices=UserSubscription.STATUS_CHOICES)
