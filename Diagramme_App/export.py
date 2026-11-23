# Nouveau fichier ajouté pour la fonctionnalité « Export Diagram » (PDF, JSON, SVG).
"""
Export d'un diagramme en PDF, JSON ou SVG.

Rappel du fonctionnement actuel (non modifié) :
  - un Diagramme est stocké en base sous forme de code PlantUML (texte) ;
  - l'image est dessinée par le serveur public PlantUML (voir Diagramme.image_url).

Ce module réutilise ces deux éléments, sans nouvelle bibliothèque à installer :
  - SVG  : on demande le SVG au même serveur PlantUML (vrai dessin vectoriel) ;
  - PDF  : on demande au serveur une image PNG haute résolution, puis on construit
           nous-mêmes un petit fichier PDF à la taille exacte du diagramme ;
  - JSON : on lit le code PlantUML enregistré et on en extrait les éléments
           (classes, attributs, méthodes, acteurs, cas d'utilisation, relations).
"""

import re                                                        # expressions régulières pour lire le PlantUML
import struct                                                    # lecture des nombres binaires du PNG
import zlib                                                      # (dé)compression des données d'image

import requests                                                  # déjà utilisé par Chat_App pour appeler Groq
from django.utils import timezone                                # date de l'export dans le JSON
from django.utils.text import slugify                            # transforme le nom du projet en nom de fichier

from .models import PLANTUML_SERVEUR                             # on réutilise l'adresse du serveur déjà définie

# "https://www.plantuml.com/plantuml/svg/" -> "https://www.plantuml.com/plantuml/"
PLANTUML_BASE = PLANTUML_SERVEUR.rsplit("svg/", 1)[0]            # base commune pour les formats svg et png
DELAI_RESEAU = 30                                                # secondes max d'attente du serveur PlantUML
DPI_PDF = 150                                                    # résolution du rendu utilisé pour le PDF (net à l'impression)
MARGE_PDF = 24                                                   # marge blanche autour du diagramme dans le PDF (en points)


class ErreurExport(Exception):                                   # erreur affichée proprement à l'utilisateur
    """Levée quand un export ne peut pas être produit."""


# ---------------------------------------------------------------------------
# Nom des fichiers : projet_diagramme_de_classes -> mon_projet_class_diagram.pdf
# ---------------------------------------------------------------------------

SUFFIXES = {                                                     # suffixe du fichier selon le type de diagramme
    "classe": "class_diagram",
    "usecase": "use_case_diagram",
}


def nom_fichier(diagramme, extension):
    """Construit un nom de fichier lisible, ex : bibliotheque_class_diagram.pdf"""
    projet = slugify(diagramme.projet.nom).replace("-", "_") or "projet"   # sans accents ni espaces
    suffixe = SUFFIXES.get(diagramme.type_diagramme, "diagram")             # type du diagramme en anglais
    return f"{projet}_{suffixe}.{extension}"                                # ex : test_class_diagram.svg


# ---------------------------------------------------------------------------
# Appel au serveur PlantUML (même principe que Diagramme.image_url)
# ---------------------------------------------------------------------------

def telecharger(format_image, code):
    """Demande au serveur PlantUML le diagramme au format 'svg' ou 'png'."""
    url = PLANTUML_BASE + format_image + "/~h" + code.encode("utf-8").hex()  # même encodage hexadécimal que image_url
    try:
        reponse = requests.get(url, timeout=DELAI_RESEAU)        # appel HTTP au serveur PlantUML
    except requests.RequestException:                            # pas d'internet, serveur injoignable, délai dépassé...
        raise ErreurExport("le serveur PlantUML est injoignable (vérifiez votre connexion).")
    if reponse.status_code == 400:                               # PlantUML répond 400 quand le code a une erreur de syntaxe
        raise ErreurExport("le code PlantUML du diagramme contient une erreur de syntaxe.")
    if reponse.status_code != 200:                               # toute autre réponse inattendue
        raise ErreurExport(f"le serveur PlantUML a répondu avec le code {reponse.status_code}.")
    return reponse.content                                       # contenu binaire du fichier


# ---------------------------------------------------------------------------
# 1) Export SVG : le vrai dessin vectoriel produit par PlantUML
# ---------------------------------------------------------------------------

def exporter_svg(diagramme):
    """Renvoie le contenu du fichier SVG (bytes)."""
    contenu = telecharger("svg", diagramme.code_plantuml)        # même rendu que celui affiché dans l'application
    if b"<svg" not in contenu[:2000]:                            # sécurité : on vérifie que c'est bien un SVG
        raise ErreurExport("le serveur PlantUML n'a pas renvoyé un fichier SVG valide.")
    return contenu                                               # vectoriel : agrandissable sans perte de qualité


# ---------------------------------------------------------------------------
# 2) Export PDF : rendu haute résolution placé dans une page à la bonne taille
# ---------------------------------------------------------------------------

def code_haute_resolution(code):
    """Ajoute 'skinparam dpi' au code pour obtenir une image nette, sans modifier le diagramme enregistré."""
    reglage = f"skinparam dpi {DPI_PDF}"                         # réglage PlantUML de la résolution
    if "@startuml" in code:                                      # cas normal : on l'ajoute juste après @startuml
        return code.replace("@startuml", "@startuml\n" + reglage, 1)
    return reglage + "\n" + code                                 # code sans @startuml : on l'ajoute au début


def lire_png(png):
    """Lit un fichier PNG et renvoie ses informations utiles pour le PDF."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":                          # signature obligatoire d'un fichier PNG
        raise ErreurExport("le serveur PlantUML n'a pas renvoyé une image PNG valide.")
    infos = {"idat": b"", "plte": None}                          # données d'image et palette éventuelle
    position = 8                                                 # on saute la signature
    while position < len(png):                                   # un PNG est une suite de blocs (« chunks »)
        longueur = struct.unpack(">I", png[position:position + 4])[0]   # taille des données du bloc
        type_bloc = png[position + 4:position + 8]               # nom du bloc : IHDR, PLTE, IDAT, IEND...
        donnees = png[position + 8:position + 8 + longueur]      # contenu du bloc
        position += 12 + longueur                                # bloc suivant (4 longueur + 4 type + données + 4 CRC)
        if type_bloc == b"IHDR":                                 # en-tête : dimensions et format des pixels
            (infos["largeur"], infos["hauteur"], infos["bits"], infos["couleur"],
             _, _, infos["entrelace"]) = struct.unpack(">IIBBBBB", donnees)
        elif type_bloc == b"PLTE":                               # palette de couleurs (images indexées)
            infos["plte"] = donnees
        elif type_bloc == b"IDAT":                               # données compressées de l'image (peuvent être en plusieurs blocs)
            infos["idat"] += donnees
        elif type_bloc == b"IEND":                               # fin du fichier
            break
    if infos.get("bits") != 8 or infos.get("entrelace"):         # seuls les PNG 8 bits non entrelacés sont gérés
        raise ErreurExport("format d'image PNG non pris en charge pour le PDF.")
    return infos


def defiltrer(brut, largeur, hauteur, octets_par_pixel):
    """Décode les filtres PNG ligne par ligne (utilisé seulement pour les images avec transparence)."""
    taille_ligne = largeur * octets_par_pixel                    # nombre d'octets d'une ligne de pixels
    resultat = bytearray()                                       # pixels décodés
    precedente = bytearray(taille_ligne)                         # ligne du dessus (zéros pour la première)
    position = 0
    for _ in range(hauteur):                                     # chaque ligne commence par un octet « type de filtre »
        filtre = brut[position]
        ligne = bytearray(brut[position + 1:position + 1 + taille_ligne])
        position += 1 + taille_ligne
        for i in range(taille_ligne):                            # on annule le filtre octet par octet (norme PNG)
            gauche = ligne[i - octets_par_pixel] if i >= octets_par_pixel else 0
            haut = precedente[i]
            haut_gauche = precedente[i - octets_par_pixel] if i >= octets_par_pixel else 0
            if filtre == 1:                                      # Sub
                ligne[i] = (ligne[i] + gauche) & 0xFF
            elif filtre == 2:                                    # Up
                ligne[i] = (ligne[i] + haut) & 0xFF
            elif filtre == 3:                                    # Average
                ligne[i] = (ligne[i] + (gauche + haut) // 2) & 0xFF
            elif filtre == 4:                                    # Paeth
                p = gauche + haut - haut_gauche
                pa, pb, pc = abs(p - gauche), abs(p - haut), abs(p - haut_gauche)
                predicteur = gauche if pa <= pb and pa <= pc else (haut if pb <= pc else haut_gauche)
                ligne[i] = (ligne[i] + predicteur) & 0xFF
        resultat += ligne                                        # filtre 0 (None) : rien à faire
        precedente = ligne
    return resultat


def image_pour_pdf(infos):
    """Prépare l'image au format attendu par le PDF : (dictionnaire PDF, données compressées)."""
    largeur, couleur = infos["largeur"], infos["couleur"]
    if couleur in (0, 2, 3):                                     # gris, RGB ou palette, sans transparence :
        canaux = 3 if couleur == 2 else 1                        # le PDF sait lire directement les données PNG
        if couleur == 0:
            espace = "/DeviceGray"                               # niveaux de gris
        elif couleur == 2:
            espace = "/DeviceRGB"                                # couleurs rouge/vert/bleu
        else:
            nb = len(infos["plte"]) // 3                         # palette : liste de couleurs indexées
            espace = f"[/Indexed /DeviceRGB {nb - 1} <{infos['plte'].hex()}>]"
        dico = (f"/ColorSpace {espace} /BitsPerComponent 8 /Filter /FlateDecode "
                f"/DecodeParms << /Predictor 15 /Colors {canaux} /BitsPerComponent 8 /Columns {largeur} >>")
        return dico, infos["idat"]                               # pas besoin de décompresser : rapide
    if couleur in (4, 6):                                        # image avec transparence (gris+alpha ou RGBA)
        canaux = 2 if couleur == 4 else 4                        # nombre d'octets par pixel
        pixels = defiltrer(zlib.decompress(infos["idat"]), largeur, infos["hauteur"], canaux)
        sortie = bytearray()                                     # pixels posés sur un fond blanc (le PDF n'a pas besoin de transparence)
        for i in range(0, len(pixels), canaux):
            alpha = pixels[i + canaux - 1]                       # opacité du pixel (0 = transparent)
            for c in range(canaux - 1):                          # mélange de la couleur avec le blanc
                sortie.append((pixels[i + c] * alpha + 255 * (255 - alpha)) // 255)
        espace = "/DeviceGray" if couleur == 4 else "/DeviceRGB"
        return f"/ColorSpace {espace} /BitsPerComponent 8 /Filter /FlateDecode", zlib.compress(bytes(sortie))
    raise ErreurExport("format de couleur PNG non pris en charge pour le PDF.")


def construire_pdf(infos, titre):
    """Écrit un fichier PDF d'une page dont la taille s'adapte au diagramme."""
    largeur_pt = infos["largeur"] * 72 / DPI_PDF                 # conversion pixels -> points (1 pouce = 72 points)
    hauteur_pt = infos["hauteur"] * 72 / DPI_PDF
    page_l = largeur_pt + 2 * MARGE_PDF                          # taille de la page = diagramme + marges
    page_h = hauteur_pt + 2 * MARGE_PDF
    dico_image, donnees_image = image_pour_pdf(infos)
    titre_pdf = ("﻿" + titre).encode("utf-16-be").hex()     # titre en UTF-16 : accents et tirets conservés
    dessin = f"q {largeur_pt:.2f} 0 0 {hauteur_pt:.2f} {MARGE_PDF} {MARGE_PDF} cm /Im1 Do Q".encode()  # place l'image dans la page

    objets = [                                                   # les 6 objets qui composent le PDF
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_l:.2f} {page_h:.2f}] "
         f"/Resources << /XObject << /Im1 4 0 R >> >> /Contents 5 0 R >>").encode(),
        (f"<< /Type /XObject /Subtype /Image /Width {infos['largeur']} /Height {infos['hauteur']} "
         f"{dico_image} /Length {len(donnees_image)} >>\nstream\n").encode() + donnees_image + b"\nendstream",
        f"<< /Length {len(dessin)} >>\nstream\n".encode() + dessin + b"\nendstream",
        f"<< /Title <{titre_pdf}> /Creator (SmartProjects) >>".encode(),   # informations du document
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")            # en-tête standard d'un fichier PDF
    positions = []                                               # position de chaque objet (table « xref »)
    for numero, objet in enumerate(objets, start=1):
        positions.append(len(pdf))
        pdf += f"{numero} 0 obj\n".encode() + objet + b"\nendobj\n"
    debut_xref = len(pdf)                                        # table des positions, obligatoire en PDF
    pdf += f"xref\n0 {len(objets) + 1}\n0000000000 65535 f \n".encode()
    for pos in positions:
        pdf += f"{pos:010d} 00000 n \n".encode()
    pdf += (f"trailer\n<< /Size {len(objets) + 1} /Root 1 0 R /Info 6 0 R >>\n"
            f"startxref\n{debut_xref}\n%%EOF\n").encode()
    return bytes(pdf)


def exporter_pdf(diagramme):
    """Renvoie le contenu du fichier PDF (bytes)."""
    png = telecharger("png", code_haute_resolution(diagramme.code_plantuml))  # même diagramme, rendu en 150 dpi
    return construire_pdf(lire_png(png), diagramme.titre)


# ---------------------------------------------------------------------------
# 3) Export JSON : structure complète lue depuis le code PlantUML
# ---------------------------------------------------------------------------

NOM = r'(?:"([^"]+)"|([\w.]+))'                                   # un nom : "entre guillemets" ou un mot simple
RE_ACTEUR = re.compile(r'^actor\s+(?:"([^"]+)"|:([^:]+):|([\w.]+))(?:\s+as\s+([\w.]+))?', re.I)          # actor "Nom" as A
RE_CAS = re.compile(r'^usecase\s+(?:"([^"]+)"|\(([^)]+)\)|([\w.]+))(?:\s+as\s+([\w.]+))?', re.I)        # usecase "Nom" as UC1
RE_CLASSE = re.compile(r'^(abstract\s+class|abstract|class|interface|enum)\s+' + NOM +                  # class Livre {
                       r'(?:\s+as\s+([\w.]+))?[^{]*(\{)?\s*(\})?\s*$', re.I)   # (\})? : classe vide « class A {} »
RE_SYSTEME = re.compile(r'^(?:rectangle|package)\s+' + NOM, re.I)                                        # rectangle "Système" {
EXTREMITE = r'("[^"]+"|\([^)]+\)|:[^:]+:|[\w.]+)'                                                         # A, "A", (Cas), :Acteur:
RE_RELATION = re.compile(r'^' + EXTREMITE + r'\s*(?:"([^"]*)")?\s*'                                     # extrémité de départ (+ cardinalité)
                         r'([<|*o#x}{+^]*(?:-+|\.+)(?:(?:left|right|up|down|l|r|u|d)(?:-+|\.+))?[|>*o#x{}+^]*)'  # la flèche
                         r'\s*(?:"([^"]*)")?\s*' + EXTREMITE + r'\s*(?::\s*(.+))?$', re.I)              # extrémité d'arrivée + label
VISIBILITES = {"-": "private", "+": "public", "#": "protected", "~": "package"}                         # symboles UML de visibilité


def type_relation(fleche, label):
    """Traduit une flèche PlantUML en type de relation UML."""
    if "<<include>>" in label:                                   # cas d'utilisation : inclusion
        return "include"
    if "<<extend>>" in label:                                    # cas d'utilisation : extension
        return "extend"
    if "|>" in fleche or "<|" in fleche:                         # triangle : héritage (ou réalisation en pointillés)
        return "realisation" if "." in fleche else "heritage"
    if "*" in fleche:                                            # losange plein
        return "composition"
    if fleche.startswith("o") or fleche.endswith("o"):           # losange vide
        return "agregation"
    if "." in fleche:                                            # pointillés simples
        return "dependance"
    return "association"                                         # trait plein


def lire_membre(ligne):
    """Analyse une ligne d'attribut ou de méthode à l'intérieur d'une classe."""
    visibilite = VISIBILITES.get(ligne[0]) if ligne[0] in VISIBILITES else None   # -, +, #, ~
    texte = ligne[1:].strip() if visibilite else ligne.strip()   # on enlève le symbole de visibilité
    texte = re.sub(r"\{(static|abstract|classifier)\}\s*", "", texte)            # modificateurs PlantUML
    est_methode = "(" in texte                                   # une méthode contient des parenthèses
    if est_methode:                                              # ex : emprunter(date : Date) : bool
        m = re.match(r"^(.*?\))\s*(?::\s*(.+))?$", texte)
        nom, type_ = (m.group(1), m.group(2)) if m else (texte, None)
    elif ":" in texte:                                           # ex : titre : String
        nom, type_ = [p.strip() for p in texte.split(":", 1)]
    elif " " in texte:                                           # ex : String titre (notation Java)
        type_, nom = texte.rsplit(" ", 1)
    else:                                                        # juste un nom
        nom, type_ = texte, None
    membre = {"nom": nom.strip(), "type": type_.strip() if type_ else None, "visibilite": visibilite}
    return membre, est_methode


def analyser_plantuml(code):
    """Lit le code PlantUML et renvoie tous les éléments du diagramme avec des identifiants."""
    elements = {"systeme": None, "acteurs": [], "cas_utilisation": [], "classes": [],
                "relations": [], "lignes_non_interpretees": []}  # rien n'est perdu : voir aussi "code_plantuml"
    index = {}                                                   # nom ou alias -> élément (pour relier les relations)
    classe_ouverte = None                                        # classe dont on lit actuellement les membres

    def enregistrer(liste, element, *cles):                      # ajoute un élément et le rend retrouvable par ses noms
        liste.append(element)
        for cle in cles:
            if cle:
                index[cle] = element
        return element

    def retrouver(extremite):                                    # trouve (ou crée) l'élément visé par une relation
        brut = extremite.strip()
        nom = brut.strip('"')
        if brut.startswith("(") and brut.endswith(")"):          # (Nom du cas) : cas d'utilisation
            nom = brut[1:-1].strip()
            if nom not in index:                                 # cas écrit directement dans la relation
                ident = f"UC{len(elements['cas_utilisation']) + 1}"
                enregistrer(elements["cas_utilisation"], {"id": ident, "nom": nom, "implicite": True}, nom, brut)
        elif brut.startswith(":") and brut.endswith(":"):        # :Nom: : acteur
            nom = brut[1:-1].strip()
            if nom not in index:
                enregistrer(elements["acteurs"], {"id": nom, "nom": nom, "implicite": True}, nom, brut)
        elif nom not in index:                                   # nom inconnu : PlantUML crée une classe automatiquement
            enregistrer(elements["classes"], {"id": nom, "nom": nom, "type": "class",
                                              "attributs": [], "methodes": [], "implicite": True}, nom)
        return index[nom]

    for numero, ligne_brute in enumerate(code.splitlines(), start=1):   # lecture ligne par ligne
        ligne = ligne_brute.strip()
        if not ligne or ligne.startswith("'"):                   # ligne vide ou commentaire PlantUML
            continue
        if classe_ouverte is not None:                           # on est à l'intérieur d'une classe { ... }
            if ligne.startswith("}"):                            # fin de la classe
                classe_ouverte = None
            elif not re.match(r"^(--|==|\.\.|__)", ligne):       # on ignore les séparateurs visuels
                membre, est_methode = lire_membre(ligne)
                classe_ouverte["methodes" if est_methode else "attributs"].append(membre)
            continue
        if ligne.startswith("@") or ligne == "}" or re.match(r"^(skinparam|left to right|top to bottom|hide|show|title)\b", ligne, re.I):
            continue                                             # réglages d'affichage : pas des éléments UML
        m = RE_ACTEUR.match(ligne)
        if m:                                                    # actor "Etudiant"
            nom = m.group(1) or m.group(2) or m.group(3)
            alias = m.group(4)
            enregistrer(elements["acteurs"], {"id": alias or nom, "nom": nom}, nom, alias, f'"{nom}"')
            continue
        m = RE_CAS.match(ligne)
        if m:                                                    # usecase "Rechercher un livre" as UC1
            nom = m.group(1) or m.group(2) or m.group(3)
            alias = m.group(4) or f"UC{len(elements['cas_utilisation']) + 1}"
            enregistrer(elements["cas_utilisation"], {"id": alias, "nom": nom}, nom, alias, f"({nom})")
            continue
        m = RE_CLASSE.match(ligne)
        if m:                                                    # class Livre {
            mot_cle = " ".join(m.group(1).lower().split())
            nom = m.group(2) or m.group(3)
            alias = m.group(4)
            type_ = {"abstract": "abstract class"}.get(mot_cle, mot_cle)
            classe = index.get(nom) if nom in index and index[nom] in elements["classes"] else None
            if classe is None:                                   # nouvelle classe
                classe = enregistrer(elements["classes"], {"id": alias or nom, "nom": nom, "type": type_,
                                                           "attributs": [], "methodes": []}, nom, alias)
            classe["type"] = type_
            classe.pop("implicite", None)                        # elle est maintenant déclarée explicitement
            if m.group(5) and not m.group(6):                    # accolade ouvrante (non refermée) : les membres suivent
                classe_ouverte = classe
            continue
        m = RE_SYSTEME.match(ligne)
        if m:                                                    # rectangle "Nom du système" {
            elements["systeme"] = m.group(1) or m.group(2)
            continue
        m = RE_RELATION.match(ligne)
        if m:                                                    # A --> B : label
            depart, card_depart, fleche, card_arrivee, arrivee, label = m.groups()
            label = (label or "").strip()
            source, cible = retrouver(depart), retrouver(arrivee)
            if fleche.startswith("<|") or fleche.startswith("<"):   # flèche écrite à l'envers : on remet dans le bon sens
                source, cible = cible, source
                card_depart, card_arrivee = card_arrivee, card_depart
            relation = {"id": f"R{len(elements['relations']) + 1}",    # identifiant unique de la relation
                        "type": type_relation(fleche, label),
                        "de": source["id"], "vers": cible["id"],        # identifiants des éléments reliés
                        "label": re.sub(r"<<(include|extend)>>", "", label).strip() or None,
                        "cardinalite_de": card_depart, "cardinalite_vers": card_arrivee,
                        "fleche_plantuml": fleche}                       # flèche d'origine, pour référence
            elements["relations"].append(relation)
            continue
        elements["lignes_non_interpretees"].append({"ligne": numero, "texte": ligne})   # signalé, pas perdu
    return elements


def exporter_json(diagramme):
    """Renvoie un dictionnaire Python prêt à être écrit en JSON."""
    return {
        "format": "smartprojects-diagramme",                     # pour reconnaître le fichier plus tard
        "version": 1,
        "exporte_le": timezone.now().isoformat(),                # date et heure de l'export
        "projet": {"id": diagramme.projet.pk, "nom": diagramme.projet.nom},
        "diagramme": {
            "id": diagramme.pk,
            "titre": diagramme.titre,
            "type": diagramme.type_diagramme,                    # "usecase" ou "classe"
            "type_libelle": diagramme.get_type_diagramme_display(),
            "source": diagramme.source,                          # "ia" ou "manuel"
            "cree_le": diagramme.created_at.isoformat(),
            "modifie_le": diagramme.updated_at.isoformat(),
        },
        "elements": analyser_plantuml(diagramme.code_plantuml),  # classes, acteurs, cas, relations...
        "code_plantuml": diagramme.code_plantuml,                # code complet : permet de redessiner le diagramme
    }
