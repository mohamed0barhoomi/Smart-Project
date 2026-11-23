"""
Client Groq très simple, avec fallback entre plusieurs modèles.

Groq propose une API compatible avec celle d'OpenAI : on envoie une requête
HTTP POST avec la liste des messages, et on reçoit la réponse du modèle en JSON.
On utilise la bibliothèque « requests » pour faire cette requête HTTP.

Fallback : settings.GROQ_MODELS contient plusieurs modèles. On essaie le premier ;
s'il échoue (erreur réseau, quota dépassé, modèle retiré, réponse illisible...),
on passe automatiquement au suivant.
"""

import json

import requests
from django.conf import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class ErreurLLM(Exception):
    """Erreur levée quand AUCUN modèle n'a pu répondre."""


def extraire_json(texte):
    """Récupère l'objet JSON contenu dans la réponse du modèle.
    Certains modèles ajoutent du texte ou des ``` autour : on garde
    uniquement ce qui se trouve entre la première { et la dernière }."""
    debut = texte.find("{")
    fin = texte.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("Pas de JSON dans la réponse")
    return json.loads(texte[debut : fin + 1])


def appeler_llm(messages, format_json=False):
    """Envoie la conversation au LLM et renvoie (reponse, nom_du_modele).

    - messages : liste de dictionnaires {"role": "system"|"user"|"assistant", "content": "..."}
    - format_json : si True, on demande un JSON et on renvoie directement un dict Python.
    """
    if not settings.GROQ_API_KEY:
        raise ErreurLLM("Clé GROQ_API_KEY manquante : ajoutez-la dans le fichier .env")

    erreurs = []
    for modele in settings.GROQ_MODELS:
        donnees = {
            "model": modele,
            "messages": messages,
            "temperature": 0.3,       # faible = réponses plus stables
        }
        if format_json:
            # Mode JSON de l'API : le modèle est obligé de répondre en JSON valide
            donnees["response_format"] = {"type": "json_object"}

        try:
            reponse = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json=donnees,
                timeout=60,
            )
            reponse.raise_for_status()   # lève une erreur si le code HTTP n'est pas 2xx
            texte = reponse.json()["choices"][0]["message"]["content"]

            if format_json:
                return extraire_json(texte), modele   # ValueError si JSON invalide -> modèle suivant
            return texte.strip(), modele

        except (requests.RequestException, KeyError, ValueError) as e:
            # On note l'erreur et on passe au modèle suivant (c'est ça, le fallback)
            erreurs.append(f"{modele} : {e}")
            print(f"[Groq] échec avec {modele} -> {e}")
            continue

    raise ErreurLLM("Aucun modèle n'a répondu. " + " | ".join(erreurs))
