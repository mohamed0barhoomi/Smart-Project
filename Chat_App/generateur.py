"""
Partie « intelligente » de SmartProjects (volontairement simple).

1. repondre_au_chat()  : l'IA joue le rôle d'un analyste qui pose des questions
                         pour mieux comprendre le projet.
2. generer_analyse()   : à partir de toute la conversation, l'IA renvoie un JSON
                         avec les besoins, les cas d'utilisation et les classes.
3. Le code Python transforme ce JSON en code PlantUML (on ne demande pas
   directement du PlantUML à l'IA : un JSON est plus fiable et plus facile à contrôler).
"""

from django.db import transaction

from Besoin_App.models import Besoin
from Diagramme_App.models import Diagramme

from .groq_client import ErreurLLM, appeler_llm

PROMPT_CHAT = """Tu es un analyste fonctionnel qui aide un étudiant à décrire son projet logiciel.
Réponds en français, en 2 à 5 phrases maximum.
Reformule brièvement ce que tu as compris, puis pose UNE ou DEUX questions utiles
(acteurs, fonctionnalités principales, contraintes de sécurité ou de performance...).
Quand la description te semble suffisante, dis-le et invite l'utilisateur à cliquer
sur « Générer »."""

PROMPT_ANALYSE = """Tu es un analyste UML. À partir de la description du projet,
produis UNIQUEMENT un objet JSON (sans texte autour) avec exactement cette structure :

{
  "besoins_fonctionnels": [
    {"titre": "...", "description": "...", "priorite": "haute|moyenne|basse"}
  ],
  "besoins_non_fonctionnels": [
    {"titre": "...", "description": "...", "priorite": "haute|moyenne|basse",
     "categorie": "performance|securite|ergonomie|disponibilite|maintenabilite|portabilite|autre"}
  ],
  "cas_utilisation": {
    "acteurs": ["NomActeur"],
    "cas": [{"nom": "Verbe à l'infinitif + complément", "acteurs": ["NomActeur"]}],
    "relations": [{"de": "nom du cas", "vers": "nom du cas", "type": "include|extend"}]
  },
  "classes": {
    "classes": [{"nom": "NomClasse", "attributs": ["nom : Type"], "methodes": ["nomMethode()"]}],
    "relations": [{"de": "ClasseA", "vers": "ClasseB",
                   "type": "association|heritage|composition|agregation",
                   "label": "texte court ou vide"}]
  }
}

Règles : 5 à 10 besoins fonctionnels, 3 à 6 non fonctionnels, 4 à 8 classes
(OBLIGATOIRE : au moins 4 classes, reliées entre elles par au moins 3 relations).
Utilise EXACTEMENT les clés du modèle ci-dessus (en français : "nom", "attributs", "methodes", "de", "vers").
Tout est en français, les noms de classes en PascalCase sans accents.
Pour "heritage", "de" est la classe fille et "vers" la classe mère."""

# Minimum attendu : en dessous, on considère la réponse de l'IA comme incomplète
MIN_CLASSES = 4


def conversation_pour_llm(projet):
    """Transforme les messages enregistrés en base au format attendu par l'API."""
    historique = []
    for message in projet.messages.all():
        historique.append({"role": message.role, "content": message.contenu})
    return historique


def repondre_au_chat(projet):
    messages = [{"role": "system", "content": PROMPT_CHAT}]
    messages.append({"role": "system", "content": f"Nom du projet : {projet.nom}. {projet.description}"})
    messages += conversation_pour_llm(projet)
    return appeler_llm(messages)          # -> (texte, modele)


# ---------------------------------------------------------------------------
# Conversion JSON -> PlantUML
# ---------------------------------------------------------------------------

def nettoyer(nom):
    """Supprime les guillemets qui casseraient la syntaxe PlantUML."""
    return str(nom).replace('"', "'").strip()


# ---------------------------------------------------------------------------
# Lecture tolérante du JSON
# Les modèles ne respectent pas toujours exactement les clés demandées
# (ex : "name" au lieu de "nom"). Sans ces fonctions, les éléments avec une
# autre clé étaient ignorés sans aucun message : c'est pour ça que le
# diagramme de classes n'avait qu'une seule classe.
# ---------------------------------------------------------------------------

def lire(d, *cles, defaut=None):
    """Renvoie la valeur de la première clé présente dans le dictionnaire d."""
    if not isinstance(d, dict):
        return defaut
    for cle in cles:
        if d.get(cle) not in (None, ""):
            return d[cle]
    return defaut


def en_liste(valeur):
    """Garantit une liste (le modèle renvoie parfois un seul élément ou un texte)."""
    if valeur is None:
        return []
    if isinstance(valeur, list):
        return valeur
    return [valeur]


def en_texte(element):
    """Un attribut/méthode peut être un texte ("nom : String")
    ou un objet ({"nom": "nom", "type": "String"}) : on le convertit en texte."""
    if isinstance(element, dict):
        nom = lire(element, "nom", "name", "attribut", "methode", defaut="")
        type_ = lire(element, "type", "type_retour", "returnType", defaut="")
        return f"{nom} : {type_}" if type_ else str(nom)
    return str(element)


def nom_de(element):
    """Nom d'un cas, d'un acteur ou d'une classe (texte ou objet)."""
    if isinstance(element, dict):
        return lire(element, "nom", "name", "titre", "nom_classe", "classe", "label", defaut="")
    return str(element or "")


def json_vers_usecase(donnees, titre_systeme):
    lignes = ["@startuml", "left to right direction", "skinparam packageStyle rectangle"]

    for acteur in en_liste(lire(donnees, "acteurs", "actors", defaut=[])):
        if nom_de(acteur):
            lignes.append(f'actor "{nettoyer(nom_de(acteur))}"')

    lignes.append(f'rectangle "{nettoyer(titre_systeme)}" {{')
    # Chaque cas reçoit un alias court (UC1, UC2...) pour écrire les liens facilement
    alias = {}
    cas_liste = [c for c in en_liste(lire(donnees, "cas", "cas_utilisation", "use_cases", "usecases", defaut=[]))
                 if nom_de(c)]   # ignore les cas sans nom
    for i, cas in enumerate(cas_liste, start=1):
        alias[nom_de(cas)] = f"UC{i}"
        lignes.append(f'  usecase "{nettoyer(nom_de(cas))}" as UC{i}')
    lignes.append("}")

    for cas in cas_liste:
        acteurs_du_cas = lire(cas, "acteurs", "actors", "acteur", "actor", defaut=[]) if isinstance(cas, dict) else []
        for acteur in en_liste(acteurs_du_cas):
            lignes.append(f'"{nettoyer(nom_de(acteur))}" --> {alias[nom_de(cas)]}')

    for rel in en_liste(lire(donnees, "relations", defaut=[])):
        de = alias.get(lire(rel, "de", "from", "source", defaut=""))
        vers = alias.get(lire(rel, "vers", "to", "cible", "target", defaut=""))
        if de and vers:
            type_rel = "extend" if lire(rel, "type", defaut="") == "extend" else "include"
            lignes.append(f"{de} ..> {vers} : <<{type_rel}>>")

    lignes.append("@enduml")
    return "\n".join(lignes)


# Flèches PlantUML pour chaque type de relation entre classes
FLECHES = {
    "heritage": "--|>",
    "composition": "*--",
    "agregation": "o--",
    "association": "--",
}


def nom_classe(nom):
    """Un nom de classe PlantUML ne doit pas contenir d'espace."""
    return nettoyer(nom).replace(" ", "")


def lire_classes(donnees):
    """Renvoie (liste des classes, liste des relations), quelle que soit la forme du JSON :
    {"classes": [...], "relations": [...]}  ou directement une liste de classes."""
    if isinstance(donnees, list):
        return donnees, []
    classes = en_liste(lire(donnees, "classes", "class", defaut=[]))
    relations = en_liste(lire(donnees, "relations", "associations", defaut=[]))
    return classes, relations


def json_vers_classes(donnees):
    """Renvoie (code PlantUML, nombre de classes réellement dessinées)."""
    lignes = ["@startuml", "skinparam classAttributeIconSize 0"]
    classes, relations = lire_classes(donnees)

    nb_classes = 0
    for classe in classes:
        nom = nom_de(classe)
        if not nom:
            continue
        nb_classes += 1
        lignes.append(f"class {nom_classe(nom)} {{")
        if isinstance(classe, dict):
            for attribut in en_liste(lire(classe, "attributs", "attributes", "proprietes", defaut=[])):
                lignes.append(f"  - {nettoyer(en_texte(attribut))}")
            for methode in en_liste(lire(classe, "methodes", "methods", "operations", defaut=[])):
                lignes.append(f"  + {nettoyer(en_texte(methode))}")
        lignes.append("}")

    for rel in relations:
        de = lire(rel, "de", "from", "source", defaut="")
        vers = lire(rel, "vers", "to", "cible", "target", defaut="")
        if not de or not vers:
            continue
        type_rel = str(lire(rel, "type", defaut="association")).lower()
        type_rel = type_rel.replace("é", "e").replace("è", "e")   # "héritage" -> "heritage"
        fleche = FLECHES.get(type_rel, "--")
        ligne = f"{nom_classe(de)} {fleche} {nom_classe(vers)}"
        label = lire(rel, "label", "nom", "name", defaut="")
        if label:
            ligne += f" : {nettoyer(label)}"
        lignes.append(ligne)

    lignes.append("@enduml")
    return "\n".join(lignes), nb_classes


# ---------------------------------------------------------------------------
# Génération complète
# ---------------------------------------------------------------------------

def compter_classes(donnees):
    classes, _ = lire_classes(lire(donnees, "classes", "diagramme_classes", defaut={}))
    return len([c for c in classes if nom_de(c)])


def generer_analyse(projet):
    """Appelle l'IA puis enregistre les besoins et les 2 diagrammes en base.
    Les éléments générés précédemment par l'IA sont remplacés ;
    ceux ajoutés à la main par l'utilisateur sont conservés.

    Renvoie (nom_du_modele, avertissement). avertissement vaut "" si tout va bien."""

    messages = [{"role": "system", "content": PROMPT_ANALYSE}]
    texte_projet = f"Projet : {projet.nom}\n{projet.description}\n\nConversation :\n"
    for m in projet.messages.filter(role="user"):
        texte_projet += f"- {m.contenu}\n"
    messages.append({"role": "user", "content": texte_projet})

    donnees, modele = appeler_llm(messages, format_json=True)

    # Diagramme de classes trop pauvre ? On redemande UNE fois à l'IA en le lui signalant.
    nb = compter_classes(donnees)
    if nb < MIN_CLASSES:
        print(f"[Génération] seulement {nb} classe(s) reçue(s) de {modele} -> nouvel essai")
        messages.append({"role": "assistant", "content": str(donnees)})
        messages.append({"role": "user", "content":
            f"Ta réponse ne contient que {nb} classe(s). Renvoie le JSON COMPLET avec au moins "
            f"{MIN_CLASSES} classes dans \"classes\" -> \"classes\" et leurs relations."})
        try:
            nouvelles, modele2 = appeler_llm(messages, format_json=True)
            if compter_classes(nouvelles) > nb:      # on garde la meilleure des deux réponses
                donnees, modele = nouvelles, modele2
        except ErreurLLM:
            pass   # on garde la première réponse

    nb_final = enregistrer_analyse(projet, donnees)
    avertissement = ""
    if nb_final < MIN_CLASSES:
        avertissement = (f"Le diagramme de classes ne contient que {nb_final} classe(s). "
                         "Précisez les données manipulées dans le chat puis régénérez, "
                         "ou complétez le diagramme à la main.")
    return modele, avertissement


# transaction.atomic : toutes les écritures en base réussissent ensemble,
# ou aucune n'est gardée si une erreur arrive au milieu (pas de données à moitié créées).
@transaction.atomic
def enregistrer_analyse(projet, donnees):
    # 1) On supprime l'ancienne génération IA
    projet.besoins.filter(source="ia").delete()
    projet.diagrammes.filter(source="ia").delete()

    # 2) Besoins
    priorites_valides = {"haute", "moyenne", "basse"}
    categories_valides = {c[0] for c in Besoin.CATEGORIE_CHOICES if c[0]}

    for b in en_liste(lire(donnees, "besoins_fonctionnels", defaut=[])):
        titre = str(lire(b, "titre", "title", "nom", defaut=b if isinstance(b, str) else ""))
        if not titre:
            continue
        Besoin.objects.create(
            projet=projet, type_besoin="F", source="ia",
            titre=titre[:150], description=str(lire(b, "description", defaut="")),
            priorite=lire(b, "priorite") if lire(b, "priorite") in priorites_valides else "moyenne",
        )
    for b in en_liste(lire(donnees, "besoins_non_fonctionnels", defaut=[])):
        titre = str(lire(b, "titre", "title", "nom", defaut=b if isinstance(b, str) else ""))
        if not titre:
            continue
        Besoin.objects.create(
            projet=projet, type_besoin="NF", source="ia",
            titre=titre[:150], description=str(lire(b, "description", defaut="")),
            priorite=lire(b, "priorite") if lire(b, "priorite") in priorites_valides else "moyenne",
            categorie=lire(b, "categorie") if lire(b, "categorie") in categories_valides else "autre",
        )

    # 3) Diagrammes
    Diagramme.objects.create(
        projet=projet, type_diagramme="usecase", source="ia",
        titre=f"Cas d'utilisation — {projet.nom}",
        code_plantuml=json_vers_usecase(
            lire(donnees, "cas_utilisation", "use_cases", defaut={}), projet.nom),
    )
    code_classes, nb_classes = json_vers_classes(lire(donnees, "classes", "diagramme_classes", defaut={}))
    Diagramme.objects.create(
        projet=projet, type_diagramme="classe", source="ia",
        titre=f"Diagramme de classes — {projet.nom}",
        code_plantuml=code_classes,
    )
    return nb_classes
