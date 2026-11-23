from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from .models import User, validate_gmail


ROLES_CLIENT = [
    ('USER', 'Client particulier'),
    ('COMPANY', 'Client entreprise'),
]

NOUVEAU_MOT_DE_PASSE = {"autocomplete": "new-password"}
SANS_AUTOCOMPLETION = {"autocomplete": "off"}

ROLES_TOUS = [
    ('USER', 'Client particulier'),
    ('COMPANY', 'Client entreprise'),
    ('ADMIN', 'Administrateur'),
]


class ConnexionForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur", max_length=150,
                               widget=forms.TextInput(attrs={"autocomplete": "username"}))
    password = forms.CharField(label="Mot de passe",
                               widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class InscriptionForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur", max_length=150)
    email = forms.EmailField(label="Adresse e-mail", validators=[validate_gmail])
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    role = forms.ChoiceField(label="Type de compte", choices=ROLES_CLIENT)
    company_name = forms.CharField(label="Nom de l'entreprise", max_length=150, required=False)
    company_description = forms.CharField(label="Description de l'entreprise", widget=forms.Textarea, required=False)
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput(attrs=NOUVEAU_MOT_DE_PASSE))
    password2 = forms.CharField(label="Confirmation du mot de passe", widget=forms.PasswordInput(attrs=NOUVEAU_MOT_DE_PASSE))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cette adresse e-mail est déjà utilisée.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Les deux mots de passe ne sont pas identiques.")
        elif password1:
            try:
                validate_password(password1)
            except forms.ValidationError as e:
                self.add_error('password1', e)

        if cleaned_data.get('role') == 'COMPANY' and not cleaned_data.get('company_name'):
            self.add_error('company_name', "Le nom de l'entreprise est obligatoire pour un client entreprise.")

        return cleaned_data


class ProfilForm(forms.Form):
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    email = forms.EmailField(label="Adresse e-mail", validators=[validate_gmail])
    company_name = forms.CharField(label="Nom de l'entreprise", max_length=150, required=False)
    company_description = forms.CharField(label="Description de l'entreprise", widget=forms.Textarea, required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Cette adresse e-mail est déjà utilisée.")
        return email


class MotDePasseForm(forms.Form):
    ancien = forms.CharField(label="Mot de passe actuel",
                             widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    nouveau1 = forms.CharField(label="Nouveau mot de passe", widget=forms.PasswordInput(attrs=NOUVEAU_MOT_DE_PASSE))
    nouveau2 = forms.CharField(label="Confirmation du nouveau mot de passe",
                               widget=forms.PasswordInput(attrs=NOUVEAU_MOT_DE_PASSE))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_ancien(self):
        ancien = self.cleaned_data['ancien']
        if not self.user.check_password(ancien):
            raise forms.ValidationError("Le mot de passe actuel est incorrect.")
        return ancien

    def clean(self):
        cleaned_data = super().clean()
        nouveau1 = cleaned_data.get('nouveau1')
        nouveau2 = cleaned_data.get('nouveau2')
        if nouveau1 and nouveau2 and nouveau1 != nouveau2:
            self.add_error('nouveau2', "Les deux mots de passe ne sont pas identiques.")
        elif nouveau1:
            try:
                validate_password(nouveau1, self.user)
            except forms.ValidationError as e:
                self.add_error('nouveau1', e)
        return cleaned_data


class UtilisateurCreateForm(InscriptionForm):
    role = forms.ChoiceField(label="Rôle", choices=ROLES_TOUS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(SANS_AUTOCOMPLETION)
        self.fields["email"].widget.attrs.update(SANS_AUTOCOMPLETION)


class UtilisateurUpdateForm(ProfilForm):
    username = forms.CharField(label="Nom d'utilisateur", max_length=150,
                               widget=forms.TextInput(attrs=SANS_AUTOCOMPLETION))
    role = forms.ChoiceField(label="Rôle", choices=ROLES_TOUS)
    is_active = forms.BooleanField(label="Compte actif", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(SANS_AUTOCOMPLETION)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username


class ReinitialiserMotDePasseForm(SetPasswordForm):
    error_messages = {"password_mismatch": "Les deux mots de passe ne sont pas identiques."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Nouveau mot de passe"
        self.fields["new_password2"].label = "Confirmation du nouveau mot de passe"
        self.fields["new_password1"].help_text = ""
        for champ in self.fields.values():
            champ.widget.attrs.update(NOUVEAU_MOT_DE_PASSE)
