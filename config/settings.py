"""
Paramètres du projet SmartProjects.
Même organisation que le projet vu en classe (dossier config/).
"""

import os
from pathlib import Path

# python-dotenv : lit le fichier .env et place ses valeurs dans les variables
# d'environnement. Ainsi la clé API Groq n'est jamais écrite dans le code.
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-smartprojects-dev-key-a-changer")
DEBUG = True
ALLOWED_HOSTS = []


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Nos applications
    "Compte_App",       # inscription / connexion
    "Projet_App",       # CRUD des projets
    "Chat_App",         # chat + génération IA
    "Besoin_App",       # CRUD des besoins fonctionnels / non fonctionnels
    "Diagramme_App",    # CRUD des diagrammes (cas d'utilisation, classes)
    "Estimation_App",   # coût, délai et résumé du projet (générés par l'IA)
    "UtilisateursApp",  # utilisateur personnalisé (rôles), profil, tableau de bord
    "AbonnementsApp",   # plans, abonnements, paiements
    "EntreprisesApp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "UtilisateursApp.middleware.PasDeCachePourUtilisateursConnectes",   # bouton « retour » après déconnexion
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Tunis"
USE_I18N = True
USE_TZ = True

# Fichiers statiques (CSS, JS) : dossier static/ à la racine du projet
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentification : où aller pour se connecter, et après connexion/déconnexion
AUTH_USER_MODEL = "UtilisateursApp.User"   # utilisateur avec rôle (USER / COMPANY / ADMIN)
LOGIN_URL = "utilisateur:login"
LOGIN_REDIRECT_URL = "utilisateur:dashboard"
LOGOUT_REDIRECT_URL = "utilisateur:login"


# ---------------------------------------------------------------------------
# Groq (partie intelligente)
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Liste des modèles essayés dans l'ordre (fallback) : si le 1er échoue
# (quota, panne, modèle retiré...), on essaie le 2e, puis le 3e.
# On peut changer la liste dans .env sans toucher au code.
GROQ_MODELS = [
    m.strip()
    for m in os.getenv(
        "GROQ_MODELS",
        "openai/gpt-oss-120b,llama-3.3-70b-versatile,openai/gpt-oss-20b",
    ).split(",")
    if m.strip()
]
