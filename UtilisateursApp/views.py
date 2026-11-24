from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache

from AbonnementsApp.models import abonnement_en_cours, nb_abonnements_actifs, revenus_du_mois

from .forms import (ConnexionForm, InscriptionForm, MotDePasseForm, ProfilForm,
                    ReinitialiserMotDePasseForm, UtilisateurCreateForm, UtilisateurUpdateForm)
from .models import User


def est_admin(user):
    return user.is_superuser or user.role == 'ADMIN'


def admin_requis(vue):
    @wraps(vue)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not est_admin(request.user):
            raise PermissionDenied
        return vue(request, *args, **kwargs)
    return wrapper


def paginer(request, queryset, par_page=10):
    page = Paginator(queryset, par_page).get_page(request.GET.get('page'))
    page.plage = page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)
    return page


def _url_existe(nom):
    """True si ce nom d'URL existe dans le projet (les apps des autres membres peuvent être absentes)."""
    try:
        reverse(nom)
        return True
    except NoReverseMatch:
        return False


def _projets_disponibles():
    """True seulement si le modèle Projet des amis (related_name='projets') est installé."""
    return any(r.get_accessor_name() == 'projets' for r in User._meta.related_objects)


def _nb_projets(utilisateur):
    return utilisateur.projets.count() if _projets_disponibles() else None


def accueil(request):
    if request.user.is_authenticated:
        return redirect('utilisateur:dashboard')
    return render(request, 'accueil.html')


@never_cache
def connexion(request):
    if request.user.is_authenticated:
        return redirect('utilisateur:dashboard')

    form = ConnexionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(request,
                            username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])
        if user is None:
            form.add_error(None, "Nom d'utilisateur ou mot de passe incorrect.")
        else:
            login(request, user)
            suivant = request.GET.get('next')
            if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
                return redirect(suivant)
            return redirect('utilisateur:dashboard')

    return render(request, 'auth/login.html', {"form": form})


def deconnexion(request):
    if request.method == "POST":
        logout(request)
    return redirect('utilisateur:login')


@never_cache
def inscription(request):
    if request.user.is_authenticated:
        return redirect('utilisateur:dashboard')

    form = InscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password1'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role='USER',   # une inscription crée toujours un client (seul l'administrateur donne le rôle ADMIN)
        )
        login(request, user)
        messages.success(request, "Bienvenue ! Votre compte a été créé avec succès.")
        return redirect('utilisateur:dashboard')

    return render(request, 'auth/inscription.html', {"form": form})


MODULES_CLIENT = [
    {"titre": "Mes projets", "description": "Décrire une idée et générer les besoins et les diagrammes UML.", "url": "projet_list", "icone": "layers"},
    {"titre": "Recommandations", "description": "Les entreprises les plus adaptées à votre projet.", "url": None},
    {"titre": "Rapports", "description": "Coût, délai et résumé de vos projets.", "url": None},
    {"titre": "Espace Scrum", "description": "Backlog, sprints et suivi des tâches.", "url": None},
    {"titre": "Mon abonnement", "description": "Votre offre, ses dates et le statut de vos paiements.", "url": "abonnement:offres", "icone": "card"},
    {"titre": "Mon profil", "description": "Vos informations personnelles et votre mot de passe.", "url": "utilisateur:profil", "icone": "user"},
]


@login_required
def dashboard(request):
    if est_admin(request.user):
        return render(request, 'dashboard/admin.html', {
            "nb_total": User.objects.count(),
            "nb_clients": User.objects.filter(role='USER').count(),
            "nb_admins": User.objects.filter(role='ADMIN').count(),
            "nb_abonnements_actifs": nb_abonnements_actifs(),
            "revenus_du_mois": revenus_du_mois(),
            "derniers": User.objects.order_by('-date_joined')[:5],
        })
    modules = [m for m in MODULES_CLIENT if m["url"] and _url_existe(m["url"])]
    return render(request, 'dashboard/client.html', {
        "modules": modules,
        "abonnement": abonnement_en_cours(request.user),
        "nb_projets": _nb_projets(request.user),
    })


@login_required
def profil(request):
    return render(request, 'profil/details.html')


@login_required
def modifierProfil(request):
    user = request.user
    form = ProfilForm(request.POST or None, user=user, initial={
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
    })

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.email = data['email']
        user.save()
        messages.success(request, "Votre profil a été mis à jour.")
        return redirect('utilisateur:profil')

    return render(request, 'profil/form.html', {"form": form})


@login_required
def changerMotDePasse(request):
    form = MotDePasseForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        request.user.set_password(form.cleaned_data['nouveau1'])
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, "Votre mot de passe a été modifié.")
        return redirect('utilisateur:profil')

    return render(request, 'profil/password.html', {"form": form})


@admin_requis
def listUtilisateurs(request):
    utilisateurs = User.objects.all()
    if _projets_disponibles():
        utilisateurs = utilisateurs.annotate(nb_projets=Count('projets'))
    utilisateurs = utilisateurs.order_by('-date_joined')
    recherche = request.GET.get('q', '').strip()
    role = request.GET.get('role', '')
    actif = request.GET.get('actif', '')
    if recherche:
        utilisateurs = utilisateurs.filter(Q(username__icontains=recherche) | Q(first_name__icontains=recherche)
                                           | Q(last_name__icontains=recherche) | Q(email__icontains=recherche))
    if role in dict(User.ROLE_CHOICES):
        utilisateurs = utilisateurs.filter(role=role)
    if actif in ('1', '0'):
        utilisateurs = utilisateurs.filter(is_active=actif == '1')
    return render(request, 'utilisateur/list.html', {
        "liste": paginer(request, utilisateurs),
        "roles": User.ROLE_CHOICES,
        "recherche": recherche,
        "role": role,
        "actif": actif,
        "filtre": bool(recherche or role or actif),
    })


@admin_requis
def toggleActifUtilisateur(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if utilisateur == request.user:
            messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        else:
            utilisateur.is_active = not utilisateur.is_active
            utilisateur.save()
            etat = "activé" if utilisateur.is_active else "désactivé"
            messages.success(request, f"Le compte {utilisateur.username} a été {etat}.")
    suivant = request.POST.get('next')
    if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
        return redirect(suivant)
    return redirect('utilisateur:utilisateur_list')


@admin_requis
def detailUtilisateur(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    return render(request, 'utilisateur/details.html', {
        "utilisateur": utilisateur,
        "nb_projets": _nb_projets(utilisateur),
        "abonnement": abonnement_en_cours(utilisateur),
    })


@admin_requis
def createUtilisateur(request):
    form = UtilisateurCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password1'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role'],
        )
        messages.success(request, "L'utilisateur a été ajouté.")
        return redirect('utilisateur:utilisateur_list')

    return render(request, 'utilisateur/form.html', {"form": form})


@admin_requis
def updateUtilisateur(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    form = UtilisateurUpdateForm(request.POST or None, user=utilisateur, initial={
        "username": utilisateur.username,
        "first_name": utilisateur.first_name,
        "last_name": utilisateur.last_name,
        "email": utilisateur.email,
        "role": utilisateur.role,
        "is_active": utilisateur.is_active,
    })
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if utilisateur == request.user and (data['role'] != utilisateur.role or not data['is_active']):
            # sinon l'administrateur pourrait se bloquer lui-même
            form.add_error(None, "Vous ne pouvez pas changer votre propre rôle ni désactiver votre propre compte.")
            return render(request, 'utilisateur/form.html', {"form": form, "object": utilisateur})
        utilisateur.username = data['username']
        utilisateur.first_name = data['first_name']
        utilisateur.last_name = data['last_name']
        utilisateur.email = data['email']
        utilisateur.role = data['role']
        utilisateur.is_active = data['is_active']
        utilisateur.save()
        messages.success(request, "L'utilisateur a été modifié.")
        return redirect('utilisateur:utilisateur_list')

    return render(request, 'utilisateur/form.html', {"form": form, "object": utilisateur})


@admin_requis
def reinitialiserMotDePasse(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    form = ReinitialiserMotDePasseForm(utilisateur, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        if utilisateur == request.user:
            update_session_auth_hash(request, utilisateur)
        messages.success(request, f"Le mot de passe de {utilisateur.username} a été réinitialisé.")
        return redirect('utilisateur:utilisateur_detail', pk=utilisateur.pk)
    return render(request, 'utilisateur/password.html', {"form": form, "utilisateur": utilisateur})


@admin_requis
def deleteUtilisateur(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if utilisateur == request.user:
            return render(request, 'utilisateur/delete.html', {"utilisateur": utilisateur,
                "nb_projets": _nb_projets(utilisateur),
                "erreur": "Vous ne pouvez pas supprimer votre propre compte."})
        utilisateur.delete()
        messages.success(request, "L'utilisateur a été supprimé.")
        return redirect('utilisateur:utilisateur_list')

    return render(request, 'utilisateur/delete.html', {"utilisateur": utilisateur,
                                                       "nb_projets": _nb_projets(utilisateur)})