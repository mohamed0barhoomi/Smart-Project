from django.urls import path

from .views import (listPlans, detailPlan, createPlan, updatePlan, deletePlan,
                    listOffres, souscrire, paiement, monAbonnement, annulerAbonnement,
                    listAbonnements, detailAbonnement, updateAbonnement, deleteAbonnement,
                    listPaiements)

app_name = "abonnement"

urlpatterns = [
    # Administration des plans
    path('plans/', listPlans, name='plan_list'),
    path('plans/<int:pk>/', detailPlan, name='plan_detail'),
    path('plans/ajouter/', createPlan, name='plan_create'),
    path('plans/<int:pk>/modifier/', updatePlan, name='plan_update'),
    path('plans/<int:pk>/supprimer/', deletePlan, name='plan_delete'),

    # Parcours client
    path('offres/', listOffres, name='offres'),
    path('offres/<int:pk>/souscrire/', souscrire, name='souscrire'),
    path('paiement/<int:pk>/', paiement, name='paiement'),
    path('mon_abonnement/', monAbonnement, name='mon_abonnement'),
    path('mon_abonnement/annuler/', annulerAbonnement, name='annuler'),

    # Suivi des abonnements (administrateur)
    path('liste/', listAbonnements, name='abonnement_list'),
    path('liste/<int:pk>/', detailAbonnement, name='abonnement_detail'),
    path('liste/<int:pk>/modifier/', updateAbonnement, name='abonnement_update'),
    path('liste/<int:pk>/supprimer/', deleteAbonnement, name='abonnement_delete'),
    path('paiements/', listPaiements, name='paiement_list'),
]
