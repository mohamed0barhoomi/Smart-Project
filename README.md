# SmartProjects

Plateforme Django : l'utilisateur décrit son projet dans un **chat**, puis SmartProjects génère
les **besoins fonctionnels / non fonctionnels**, le **diagramme de cas d'utilisation** et le
**diagramme de classes**. Tout ce qui est généré peut ensuite être consulté, modifié et supprimé (CRUD).

## Lancer le projet

```bash
# 1. Créer l'environnement et installer les dépendances (comme en cours, avec uv)
uv sync
#    ou, sans uv :
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 2. Configurer la clé Groq
copy .env.example .env           # Windows  (cp sous Linux/Mac)
#    puis coller la clé de https://console.groq.com/keys dans GROQ_API_KEY

# 3. Créer la base et lancer le serveur
uv run manage.py migrate         # ou : python manage.py migrate
uv run manage.py createsuperuser # (optionnel) pour /admin
uv run manage.py runserver
```

Ouvrir http://127.0.0.1:8000, créer un compte, puis un projet.

> Sans clé Groq, toute la partie CRUD fonctionne : seul le chat affiche un message d'erreur clair.

## Structure

```
SmartProjects/
├── config/              settings.py, urls.py (même organisation qu'en cours)
├── Compte_App/          inscription (CreateView) + connexion/déconnexion (vues Django)
├── Projet_App/          modèle Projet + CRUD
│   └── mixins.py        ProjetCourantMixin : récupère le projet depuis l'URL
├── Chat_App/            modèle Message + vues du chat
│   ├── groq_client.py   appel à l'API Groq avec fallback entre 3 modèles
│   └── generateur.py    prompts + conversion JSON -> PlantUML
├── Besoin_App/          modèle Besoin + CRUD
├── Diagramme_App/       modèle Diagramme + CRUD
├── templates/           base.html + un dossier par app (comme en cours)
│   └── partials/        petits morceaux réutilisés (champs de formulaire, logo...)
└── static/css/style.css une seule feuille de style pour tout le site
```

## URLs principales

| URL | Rôle |
|---|---|
| `/projets/` | liste des projets |
| `/projets/<id>/` | aperçu d'un projet |
| `/projets/<id>/chat/` | chat + bouton « Générer » |
| `/projets/<id>/besoins/` | CRUD des besoins (filtre `?type=F` ou `?type=NF`) |
| `/projets/<id>/diagrammes/` | CRUD des diagrammes |

## Comment marche la génération

1. Chaque message du chat est enregistré (modèle `Message`).
2. Après chaque message, l'IA répond comme un analyste et pose des questions.
3. Le bouton **Générer** envoie toute la description à l'IA et lui demande un **JSON**.
4. Le code Python lit ce JSON et crée les objets `Besoin` et deux `Diagramme`.
   Les diagrammes sont stockés en **PlantUML** (du texte), affichés en image par le serveur plantuml.com.
5. Une nouvelle génération remplace les éléments marqués « IA » et garde ceux ajoutés à la main.

**Fallback** : `settings.GROQ_MODELS` contient 3 modèles. Si le premier échoue
(quota, panne, modèle retiré, JSON invalide), on essaie le suivant. Le nom du modèle
qui a répondu est affiché sous chaque message du chat.
