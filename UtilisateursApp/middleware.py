from django.utils.cache import add_never_cache_headers


class PasDeCachePourUtilisateursConnectes:
    """
    Empêche le navigateur de garder en cache les pages vues par un utilisateur connecté.

    Sans ça, après la déconnexion, la flèche « retour » du navigateur ré-affiche l'ancienne page
    (copie gardée en mémoire) comme si on était encore connecté. Avec les en-têtes
    « Cache-Control: no-store », le navigateur redemande la page au serveur, qui renvoie
    alors vers la page de connexion.

    S'applique à toutes les pages (y compris celles des autres apps) : seuls les en-têtes HTTP changent.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            add_never_cache_headers(response)
        return response
