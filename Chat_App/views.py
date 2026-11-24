from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from Projet_App.models import Projet

from .generateur import generer_analyse, repondre_au_chat
from .groq_client import ErreurLLM
from .models import Message

# Ici on utilise des vues « fonctions » (comme listeExpeditions en cours),
# plus simples à lire pour une logique qui n'est pas un CRUD classique.


@login_required
def chat(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk, proprietaire=request.user)

    if request.method == "POST":
        texte = request.POST.get("contenu", "").strip()
        if not texte:
            messages.error(request, "Le message est vide.")
            return redirect("chat", projet_pk=projet.pk)

        # 1) on enregistre le message de l'utilisateur
        Message.objects.create(projet=projet, role="user", contenu=texte)

        # 2) on demande une réponse à l'IA
        try:
            reponse, modele = repondre_au_chat(projet)
            Message.objects.create(projet=projet, role="assistant", contenu=reponse, modele=modele)
        except ErreurLLM as e:
            messages.error(request, f"L'assistant n'a pas pu répondre : {e}")

        projet.save()  # met à jour updated_at du projet
        # Redirection après un POST : évite de renvoyer le formulaire si on actualise la page
        return redirect("chat", projet_pk=projet.pk)

    return render(request, "chat/chat.html", {
        "projet": projet,
        "liste_messages": projet.messages.all(),
        "nb_besoins": projet.besoins.count(),
        "nb_diagrammes": projet.diagrammes.count(),
        "onglet": "chat",
    })


@login_required
@require_POST   # cette vue n'accepte que les requêtes POST (bouton « Générer »)
def generer(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk, proprietaire=request.user)

    if not projet.messages.filter(role="user").exists():
        messages.error(request, "Décrivez d'abord votre projet dans le chat.")
        return redirect("chat", projet_pk=projet.pk)

    try:
        modele, avertissement = generer_analyse(projet)
        messages.success(request, f"Besoins, diagrammes et estimation générés (modèle : {modele}).")
        if avertissement:
            messages.warning(request, avertissement)
        return redirect("projet_detail", pk=projet.pk)
    except ErreurLLM as e:
        messages.error(request, f"La génération a échoué : {e}")
    except Exception as e:  # réponse de l'IA inattendue
        messages.error(request, f"La réponse de l'IA n'a pas pu être traitée ({e}). Réessayez.")
    return redirect("chat", projet_pk=projet.pk)


@login_required
@require_POST
def vider_chat(request, projet_pk):
    projet = get_object_or_404(Projet, pk=projet_pk, proprietaire=request.user)
    projet.messages.all().delete()
    messages.success(request, "Conversation effacée.")
    return redirect("chat", projet_pk=projet.pk)
