from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from UtilisateursApp.views import admin_requis, paginer

from .forms import AbonnementStatutForm, PaiementForm, PlanForm
from .models import (Paiement, SubscriptionPlan, UserSubscription, abonnement_en_cours,
                     changement_en_attente, mettre_a_jour_expirations)

CARTE_REFUSEE = "4000000000000002"


@admin_requis
def listPlans(request):
    plans = SubscriptionPlan.objects.all()
    return render(request, 'abonnement/plan_list.html', {"liste": paginer(request, plans)})


@admin_requis
def detailPlan(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk)
    return render(request, 'abonnement/plan_details.html', {
        "plan": plan,
        "nb_abonnements": plan.abonnements.count(),
    })


@admin_requis
def createPlan(request):
    form = PlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        SubscriptionPlan.objects.create(**form.cleaned_data)
        messages.success(request, "Le plan a été ajouté.")
        return redirect('abonnement:plan_list')
    return render(request, 'abonnement/plan_form.html', {"form": form})


@admin_requis
def updatePlan(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk)
    form = PlanForm(request.POST or None, plan=plan, initial={
        "name": plan.name,
        "price": plan.price,
        "duration_days": plan.duration_days,
        "description": plan.description,
        "is_active": plan.is_active,
    })
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        plan.name = data['name']
        plan.price = data['price']
        plan.duration_days = data['duration_days']
        plan.description = data['description']
        plan.is_active = data['is_active']
        plan.save()
        messages.success(request, "Le plan a été modifié.")
        return redirect('abonnement:plan_list')
    return render(request, 'abonnement/plan_form.html', {"form": form, "object": plan})


@admin_requis
def deletePlan(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk)
    if request.method == "POST":
        try:
            plan.delete()
        except ProtectedError:
            return render(request, 'abonnement/plan_delete.html', {"plan": plan,
                "erreur": "Ce plan est utilisé par des abonnements : désactivez-le plutôt que de le supprimer."})
        messages.success(request, "Le plan a été supprimé.")
        return redirect('abonnement:plan_list')
    return render(request, 'abonnement/plan_delete.html', {"plan": plan})


@login_required
def listOffres(request):
    return render(request, 'abonnement/offres.html', {
        "liste": SubscriptionPlan.objects.filter(is_active=True),
        "en_cours": abonnement_en_cours(request.user),
        "en_attente": changement_en_attente(request.user),
    })


@login_required
def souscrire(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk, is_active=True)
    en_cours = abonnement_en_cours(request.user)
    if en_cours and en_cours.payment_status == 'PAID' and en_cours.plan == plan:
        messages.info(request, "C'est déjà votre plan actuel.")
        return redirect('abonnement:mon_abonnement')

    if request.method == "POST":
        UserSubscription.objects.filter(user=request.user, status='ACTIVE', payment_status='PENDING').delete()
        abonnement = UserSubscription.objects.create(user=request.user, plan=plan)
        return redirect('abonnement:paiement', pk=abonnement.pk)
    return render(request, 'abonnement/souscrire.html', {"plan": plan, "en_cours": en_cours})


@login_required
def paiement(request, pk):
    abonnement = get_object_or_404(UserSubscription, pk=pk, user=request.user,
                                   status='ACTIVE', payment_status='PENDING')
    form = PaiementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data['numero'] == CARTE_REFUSEE:
            Paiement.objects.create(subscription=abonnement, amount=abonnement.plan.price,
                                    method='CARTE', status='FAILED')
            form.add_error(None, "Paiement refusé par la banque. Essayez une autre carte.")
        else:
            Paiement.objects.create(subscription=abonnement, amount=abonnement.plan.price,
                                    method='CARTE', status='PAID')
            changement = UserSubscription.objects.filter(user=request.user, status='ACTIVE',
                                                         payment_status='PAID').update(status='CANCELLED')
            abonnement.payment_status = 'PAID'
            abonnement.start_date = date.today()
            abonnement.end_date = abonnement.start_date + timedelta(days=abonnement.plan.duration_days)
            abonnement.save()
            if changement:
                messages.success(request, f"Paiement accepté. Vous êtes passé au plan {abonnement.plan.name}.")
            else:
                messages.success(request, "Paiement accepté. Votre abonnement est actif.")
            return redirect('abonnement:mon_abonnement')
    return render(request, 'abonnement/paiement.html', {"form": form, "abonnement": abonnement})


@login_required
def monAbonnement(request):
    abonnement = abonnement_en_cours(request.user)
    jours_restants = None
    if abonnement and abonnement.end_date:
        jours_restants = (abonnement.end_date - date.today()).days
    historique = UserSubscription.objects.filter(user=request.user).select_related('plan')
    if abonnement:
        historique = historique.exclude(pk=abonnement.pk)
    return render(request, 'abonnement/mon_abonnement.html', {
        "abonnement": abonnement,
        "en_attente": changement_en_attente(request.user),
        "jours_restants": jours_restants,
        "historique": historique,
        "paiements": Paiement.objects.filter(subscription__user=request.user).select_related('subscription__plan'),
    })


@login_required
def annulerAbonnement(request):
    abonnement = abonnement_en_cours(request.user)
    if abonnement is None:
        return redirect('abonnement:mon_abonnement')
    if request.method == "POST":
        abonnement.status = 'CANCELLED'
        abonnement.save()
        messages.success(request, "Votre abonnement a été annulé.")
        return redirect('abonnement:mon_abonnement')
    return render(request, 'abonnement/annuler.html', {"abonnement": abonnement})


@admin_requis
def listAbonnements(request):
    mettre_a_jour_expirations()
    abonnements = UserSubscription.objects.select_related('user', 'plan')
    statut = request.GET.get('statut')
    if statut in dict(UserSubscription.STATUS_CHOICES):
        abonnements = abonnements.filter(status=statut)
    return render(request, 'abonnement/abonnement_list.html', {
        "liste": paginer(request, abonnements),
        "statuts": UserSubscription.STATUS_CHOICES,
        "statut": statut,
    })


@admin_requis
def detailAbonnement(request, pk):
    abonnement = get_object_or_404(UserSubscription.objects.select_related('user', 'plan'), pk=pk)
    return render(request, 'abonnement/abonnement_details.html', {
        "abonnement": abonnement,
        "paiements": abonnement.paiements.all(),
    })


@admin_requis
def updateAbonnement(request, pk):
    abonnement = get_object_or_404(UserSubscription.objects.select_related('user', 'plan'), pk=pk)
    form = AbonnementStatutForm(request.POST or None, initial={"status": abonnement.status})
    if request.method == "POST" and form.is_valid():
        abonnement.status = form.cleaned_data['status']
        abonnement.save()
        messages.success(request, "Le statut de l'abonnement a été modifié.")
        return redirect('abonnement:abonnement_detail', pk=abonnement.pk)
    return render(request, 'abonnement/abonnement_form.html', {"form": form, "abonnement": abonnement})


@admin_requis
def deleteAbonnement(request, pk):
    abonnement = get_object_or_404(UserSubscription.objects.select_related('user', 'plan'), pk=pk)
    if request.method == "POST":
        abonnement.delete()
        messages.success(request, "L'abonnement a été supprimé.")
        return redirect('abonnement:abonnement_list')
    return render(request, 'abonnement/abonnement_delete.html', {"abonnement": abonnement})


@admin_requis
def listPaiements(request):
    paiements = Paiement.objects.select_related('subscription__user', 'subscription__plan')
    statut = request.GET.get('statut')
    if statut in dict(Paiement.STATUS_CHOICES):
        paiements = paiements.filter(status=statut)
    return render(request, 'abonnement/paiement_list.html', {
        "liste": paginer(request, paiements),
        "statuts": Paiement.STATUS_CHOICES,
        "statut": statut,
    })
