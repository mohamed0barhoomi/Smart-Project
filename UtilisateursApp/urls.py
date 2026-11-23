from django.urls import path
from .views import (accueil, connexion, deconnexion, inscription, dashboard,
                    profil, modifierProfil, changerMotDePasse,
                    listUtilisateurs, detailUtilisateur, createUtilisateur,
                    updateUtilisateur, deleteUtilisateur, toggleActifUtilisateur,
                    reinitialiserMotDePasse)

app_name = "utilisateur"

urlpatterns = [
    # Accueil, connexion, inscription
    path('', accueil, name='accueil'),
    path('connexion/', connexion, name='login'),
    path('deconnexion/', deconnexion, name='logout'),
    path('inscription/', inscription, name='inscription'),

    # Tableau de bord
    path('dashboard/', dashboard, name='dashboard'),

    # Profil (client)
    path('profil/', profil, name='profil'),
    path('profil/modifier/', modifierProfil, name='profil_update'),
    path('profil/mot_de_passe/', changerMotDePasse, name='profil_password'),

    # Gestion des utilisateurs (admin)
    path('utilisateur_list/', listUtilisateurs, name='utilisateur_list'),
    path('utilisateur_detail/<int:pk>/', detailUtilisateur, name='utilisateur_detail'),
    path('utilisateur_create/', createUtilisateur, name='utilisateur_create'),
    path('utilisateur_update/<int:pk>/', updateUtilisateur, name='utilisateur_update'),
    path('utilisateur_delete/<int:pk>/', deleteUtilisateur, name='utilisateur_delete'),
    path('utilisateur_toggle/<int:pk>/', toggleActifUtilisateur, name='utilisateur_toggle'),
    path('utilisateur_password/<int:pk>/', reinitialiserMotDePasse, name='utilisateur_password'),
]