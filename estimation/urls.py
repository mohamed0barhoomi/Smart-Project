from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('connexion/', auth_views.LoginView.as_view(template_name='estimation/connexion.html'), name='connexion'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='deconnexion'),

    # Mêmes chemins que SmartProjects : projets/<id du projet>/estimation/...
    path('projets/<int:projet_pk>/estimation/modifier/', views.modifier_estimation, name='modifier_estimation'),
    path('projets/<int:projet_pk>/estimation/supprimer/', views.supprimer_estimation, name='supprimer_estimation'),
]
