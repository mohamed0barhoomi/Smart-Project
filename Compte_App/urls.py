from django.contrib.auth import views as auth_views
from django.urls import path

from .views import InscriptionView

urlpatterns = [
    # LoginView et LogoutView sont fournies par Django : pas besoin de les coder.
    path("connexion/", auth_views.LoginView.as_view(template_name="compte/connexion.html"), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("inscription/", InscriptionView.as_view(), name="inscription"),
]
