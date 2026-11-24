import unittest
from datetime import date, timedelta

from django.apps import apps

from django.test import TestCase
from django.urls import reverse

from AbonnementsApp.models import SubscriptionPlan, UserSubscription

from .models import User


class PagesDesignTests(TestCase):
    """Chaque page s'affiche (200) avec la bonne mise en page et le bon menu selon le rôle."""

    def setUp(self):
        self.admin = User.objects.create_user('admin1', 'admin1@gmail.com', 'MotDePasse!123', role='ADMIN')
        self.particulier = User.objects.create_user('part1', 'part1@gmail.com', 'MotDePasse!123', role='USER')
        self.autre_client = User.objects.create_user('cli1', 'cli1@gmail.com', 'MotDePasse!123', role='USER')
        self.plan = SubscriptionPlan.objects.create(name='Pro', price='49.90', duration_days=30, description='Offre pro')
        self.abonnement = UserSubscription.objects.create(user=self.particulier, plan=self.plan, payment_status='PAID',
                                                          end_date=date.today() + timedelta(30))

    def verifier(self, url, sidebar=True, actif=None):
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200, url)
        if not url.endswith(('/connexion/', '/inscription/')):   # pages « lampe » : leur propre CSS
            self.assertContains(reponse, 'css/app.css')
        if sidebar:
            self.assertContains(reponse, 'class="sidebar"')
        else:
            self.assertNotContains(reponse, 'class="sidebar"')
        if actif:
            # tolérant aux deux balisages (projet autonome : class avant href, projet intégré : href avant class)
            self.assertRegex(reponse.content.decode(),
                             r'(href="%s" class="nav-link (is-)?active"|class="nav-link (is-)?active" href="%s")' % (actif, actif), url)
        return reponse

    def test_pages_publiques_sans_sidebar(self):
        for nom in ['accueil', 'login', 'inscription']:
            self.verifier(reverse(f'utilisateur:{nom}'), sidebar=False)

    def test_pages_admin(self):
        self.client.force_login(self.admin)
        u, p = self.particulier.pk, self.plan.pk
        pages = [
            ('utilisateur:dashboard', [], None),
            ('utilisateur:utilisateur_list', [], 'utilisateur:utilisateur_list'),
            ('utilisateur:utilisateur_detail', [u], 'utilisateur:utilisateur_list'),
            ('utilisateur:utilisateur_create', [], 'utilisateur:utilisateur_list'),
            ('utilisateur:utilisateur_update', [u], 'utilisateur:utilisateur_list'),
            ('utilisateur:utilisateur_delete', [u], 'utilisateur:utilisateur_list'),
            ('abonnement:plan_list', [], 'abonnement:plan_list'),
            ('abonnement:plan_detail', [p], 'abonnement:plan_list'),
            ('abonnement:plan_create', [], 'abonnement:plan_list'),
            ('abonnement:plan_update', [p], 'abonnement:plan_list'),
            ('abonnement:plan_delete', [p], 'abonnement:plan_list'),
            ('abonnement:abonnement_list', [], 'abonnement:abonnement_list'),
            ('utilisateur:profil', [], 'utilisateur:profil'),
            ('utilisateur:profil_update', [], 'utilisateur:profil'),
            ('utilisateur:profil_password', [], 'utilisateur:profil'),
        ]
        for nom, args, actif in pages:
            self.verifier(reverse(nom, args=args), actif=reverse(actif) if actif else None)

    def test_menu_admin(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse('utilisateur:dashboard'))
        for texte in ['Tableau de bord', 'Utilisateurs', "Plans d'abonnement", 'Abonnements', 'Mon profil']:
            self.assertContains(reponse, texte)
        self.assertNotContains(reponse, 'href="%s"' % reverse('abonnement:mon_abonnement'))

    def test_pages_client(self):
        self.client.force_login(self.particulier)
        mon_abonnement = reverse('abonnement:mon_abonnement')
        self.verifier(reverse('utilisateur:dashboard'))
        self.verifier(reverse('utilisateur:profil'), actif=reverse('utilisateur:profil'))
        self.verifier(reverse('abonnement:offres'), actif=reverse('abonnement:offres'))
        self.verifier(mon_abonnement, actif=mon_abonnement)
        self.verifier(reverse('abonnement:annuler'), actif=mon_abonnement)

    def test_parcours_paiement_client(self):
        self.client.force_login(self.autre_client)
        self.verifier(reverse('abonnement:souscrire', args=[self.plan.pk]))
        self.client.post(reverse('abonnement:souscrire', args=[self.plan.pk]))
        en_attente = UserSubscription.objects.get(user=self.autre_client)
        reponse = self.verifier(reverse('abonnement:paiement', args=[en_attente.pk]))
        self.assertContains(reponse, 'Paiement simulé')

    def test_menu_client(self):
        self.client.force_login(self.particulier)
        reponse = self.client.get(reverse('utilisateur:dashboard'))
        self.assertContains(reponse, 'Mon abonnement')
        for nom in ['utilisateur:utilisateur_list', 'abonnement:plan_list', 'abonnement:abonnement_list']:
            self.assertNotContains(reponse, 'href="%s"' % reverse(nom))
        # Pas de modules non développés
        for texte in ['Recommandations', 'Espace Scrum', 'Bientôt']:
            self.assertNotContains(reponse, texte)

    def test_un_seul_type_de_client(self):
        """Il n'y a plus de « client entreprise » : seulement Client et Administrateur."""
        self.assertEqual([code for code, _ in User.ROLE_CHOICES], ['USER', 'ADMIN'])
        self.assertEqual(User.ROLE_CHOICES[0][1], 'Client')
        reponse = self.client.get(reverse('utilisateur:inscription'))
        self.assertNotContains(reponse, 'company_name')
        self.assertNotContains(reponse, 'id_role')          # pas de choix de type de compte
        self.assertNotContains(reponse, 'entreprise')
        self.client.force_login(self.particulier)
        reponse = self.client.get(reverse('utilisateur:profil'))
        self.assertNotContains(reponse, 'Profil entreprise')
        self.assertNotContains(self.client.get(reverse('utilisateur:profil_update')), 'company_name')

    def test_inscription_cree_toujours_un_client(self):
        donnees = {'username': 'nouveau', 'email': 'nouveau@gmail.com', 'password1': 'MotDePasse!123',
                   'password2': 'MotDePasse!123', 'role': 'ADMIN'}   # un rôle injecté par le navigateur est ignoré
        reponse = self.client.post(reverse('utilisateur:inscription'), donnees)
        self.assertRedirects(reponse, reverse('utilisateur:dashboard'), fetch_redirect_response=False)
        self.assertEqual(User.objects.get(username='nouveau').role, 'USER')

    def test_erreurs_formulaire_en_rouge(self):
        reponse = self.client.post(reverse('utilisateur:login'), {'username': '', 'password': ''})
        self.assertContains(reponse, 'has-error')
        self.assertContains(reponse, 'class="field-error"')

    def test_message_django_affiche(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse('abonnement:plan_create'), {
            'name': 'Basic', 'price': '10', 'duration_days': 15, 'is_active': 'on'}, follow=True)
        self.assertContains(reponse, 'class="flash flash-success"')
        self.assertContains(reponse, 'Le plan a été ajouté.')

    def test_css_servi(self):
        from django.contrib.staticfiles import finders
        self.assertIsNotNone(finders.find('css/app.css'))


class GestionUtilisateursTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin1', 'admin1@gmail.com', 'MotDePasse!123', role='ADMIN')
        for i in range(12):
            User.objects.create_user(f'client{i:02d}', f'client{i:02d}@gmail.com', 'x', role='USER')
        self.ent = User.objects.create_user('acme', 'contact.acme@gmail.com', 'x', role='USER',
                                            first_name='Sarra')
        self.inactif = User.objects.create_user('dormeur', 'dormeur@gmail.com', 'x', is_active=False)
        self.client.force_login(self.admin)
        self.url = reverse('utilisateur:utilisateur_list')

    def test_pagination_10_par_page(self):
        reponse = self.client.get(self.url)
        self.assertEqual(len(reponse.context['liste']), 10)
        self.assertEqual(reponse.context['liste'].paginator.count, 15)
        self.assertContains(reponse, 'aria-label="Pagination"')
        self.assertEqual(len(self.client.get(self.url + '?page=2').context['liste']), 5)
        self.assertEqual(self.client.get(self.url + '?page=999').context['liste'].number, 2)

    def test_recherche_nom_et_email(self):
        self.assertEqual([u.username for u in self.client.get(self.url + '?q=sarra').context['liste']], ['acme'])
        self.assertEqual([u.username for u in self.client.get(self.url + '?q=contact.acme').context['liste']], ['acme'])
        self.assertContains(self.client.get(self.url + '?q=introuvable'), 'Aucun résultat')

    def test_filtres_role_et_statut(self):
        self.assertEqual(self.client.get(self.url + '?role=ADMIN').context['liste'].paginator.count, 1)
        self.assertEqual([u.username for u in self.client.get(self.url + '?actif=0').context['liste']], ['dormeur'])
        reponse = self.client.get(self.url + '?role=USER&actif=1&page=2')
        self.assertEqual(reponse.context['liste'].paginator.count, 13)
        self.assertContains(reponse, '?role=USER&amp;actif=1&amp;page=1')

    def test_activer_desactiver(self):
        url = reverse('utilisateur:utilisateur_toggle', args=[self.ent.pk])
        reponse = self.client.post(url, {'next': self.url + '?role=USER'})
        self.assertRedirects(reponse, self.url + '?role=USER')
        self.ent.refresh_from_db()
        self.assertFalse(self.ent.is_active)
        self.client.post(url)
        self.ent.refresh_from_db()
        self.assertTrue(self.ent.is_active)

    def test_toggle_soi_meme_refuse_et_get_sans_effet(self):
        self.client.post(reverse('utilisateur:utilisateur_toggle', args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.client.get(reverse('utilisateur:utilisateur_toggle', args=[self.ent.pk]))
        self.ent.refresh_from_db()
        self.assertTrue(self.ent.is_active)

    def test_toggle_redirection_externe_ignoree(self):
        reponse = self.client.post(reverse('utilisateur:utilisateur_toggle', args=[self.ent.pk]), {'next': 'https://exemple.com/'})
        self.assertRedirects(reponse, self.url)

    def test_toggle_reserve_admin(self):
        self.client.force_login(self.ent)
        self.assertEqual(self.client.post(reverse('utilisateur:utilisateur_toggle', args=[self.inactif.pk])).status_code, 403)

    def test_pagination_plans_abonnements_paiements(self):
        from AbonnementsApp.models import Paiement
        for i in range(11):
            plan = SubscriptionPlan.objects.create(name=f'Plan {i}', price=i, duration_days=30)
            abonnement = UserSubscription.objects.create(user=self.ent, plan=plan)
            Paiement.objects.create(subscription=abonnement, amount=i)
        for nom in ['abonnement:plan_list', 'abonnement:abonnement_list', 'abonnement:paiement_list']:
            reponse = self.client.get(reverse(nom))
            self.assertEqual(len(reponse.context['liste']), 10, nom)
            self.assertEqual(len(self.client.get(reverse(nom) + '?page=2').context['liste']), 1, nom)


class DesignEtape5Tests(TestCase):
    def setUp(self):
        from AbonnementsApp.models import Paiement
        self.admin = User.objects.create_user('admin1', 'admin1@gmail.com', 'x', role='ADMIN')
        self.ent = User.objects.create_user('acme', 'acme@gmail.com', 'x', role='USER')
        plan = SubscriptionPlan.objects.create(name='Pro', price='49.90', duration_days=30)
        abonnement = UserSubscription.objects.create(user=self.ent, plan=plan, payment_status='PAID',
                                                     end_date=date.today() + timedelta(30))
        Paiement.objects.create(subscription=abonnement, amount='49.90', status='PAID')
        Paiement.objects.create(subscription=abonnement, amount='19.00', status='FAILED')
        self.client.force_login(self.admin)

    def test_statistiques_dashboard(self):
        reponse = self.client.get(reverse('utilisateur:dashboard'))
        self.assertEqual(str(reponse.context['revenus_du_mois']), '49.90')
        for texte in ['Utilisateurs', 'Abonnements actifs', 'Revenus du mois', '49,90']:
            self.assertContains(reponse, texte)
        self.assertNotContains(reponse, 'Entreprises')

    def test_badges_couleurs(self):
        reponse = self.client.get(reverse('abonnement:paiement_list'))
        self.assertContains(reponse, 'badge-success">Payé')
        self.assertContains(reponse, 'badge-danger">Échoué')
        reponse = self.client.get(reverse('utilisateur:utilisateur_list'))
        self.assertContains(reponse, 'badge-dark')
        self.assertNotContains(reponse, 'badge-company')

    def test_modale_sur_chaque_suppression(self):
        pages = [reverse('utilisateur:utilisateur_list'), reverse('abonnement:plan_list'),
                 reverse('abonnement:abonnement_list'),
                 reverse('utilisateur:utilisateur_detail', args=[self.ent.pk]),
                 reverse('abonnement:plan_detail', args=[SubscriptionPlan.objects.get().pk]),
                 reverse('abonnement:abonnement_detail', args=[UserSubscription.objects.get().pk])]
        for url in pages:
            reponse = self.client.get(url)
            self.assertContains(reponse, 'id="modale-confirmation"')
            self.assertContains(reponse, 'data-confirm="Voulez-vous vraiment supprimer')



class MotsDePasseEtModificationTests(TestCase):
    MDP_ADMIN = 'AdminSecret!2026'
    MDP_CLIENT = 'ClientSecret!2026'

    def setUp(self):
        self.admin = User.objects.create_user('admin1', 'admin1@gmail.com', self.MDP_ADMIN, role='ADMIN')
        self.cible = User.objects.create_user('cible', 'cible@gmail.com', self.MDP_CLIENT, first_name='Ancien')

    def connecter(self, username, mdp):
        self.assertTrue(self.client.login(username=username, password=mdp))

    def toujours_connecte(self):
        return self.client.get(reverse('utilisateur:profil')).status_code == 200

    def test_admin_modifie_un_utilisateur_et_pas_lui_meme(self):
        self.connecter('admin1', self.MDP_ADMIN)
        hash_admin = User.objects.get(pk=self.admin.pk).password
        reponse = self.client.post(reverse('utilisateur:utilisateur_update', args=[self.cible.pk]), {
            'username': 'cible', 'first_name': 'Nouveau', 'last_name': 'Nom', 'email': 'nouveau.cible@gmail.com',
            'role': 'ADMIN', 'is_active': 'on'})
        self.assertRedirects(reponse, reverse('utilisateur:utilisateur_list'))
        self.cible.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual((self.cible.first_name, self.cible.email, self.cible.role),
                         ('Nouveau', 'nouveau.cible@gmail.com', 'ADMIN'))
        self.assertEqual((self.admin.first_name, self.admin.email, self.admin.role), ('', 'admin1@gmail.com', 'ADMIN'))
        self.assertEqual(self.admin.password, hash_admin)
        self.assertTrue(self.cible.check_password(self.MDP_CLIENT))

    def test_identifiant_de_l_admin_injecte_par_le_navigateur(self):
        self.connecter('admin1', self.MDP_ADMIN)
        reponse = self.client.post(reverse('utilisateur:utilisateur_update', args=[self.cible.pk]), {
            'username': 'admin1', 'email': 'cible@gmail.com', 'role': 'USER', 'is_active': 'on'})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Ce nom d&#x27;utilisateur est déjà utilisé.")
        self.assertContains(reponse, "corrigez les champs en rouge")
        self.cible.refresh_from_db()
        self.assertEqual(self.cible.username, 'cible')

    def test_formulaire_admin_sans_mot_de_passe_ni_autocompletion(self):
        self.connecter('admin1', self.MDP_ADMIN)
        html = self.client.get(reverse('utilisateur:utilisateur_update', args=[self.cible.pk])).content.decode()
        self.assertNotIn('type="password"', html)
        self.assertIn('<form method="post" class="panel" autocomplete="off"', html)
        self.assertIn('name="username" value="cible" autocomplete="off"', html)
        self.assertIn(reverse('utilisateur:utilisateur_password', args=[self.cible.pk]), html)

    def test_admin_reinitialise_le_mot_de_passe_d_un_utilisateur(self):
        self.connecter('admin1', self.MDP_ADMIN)
        url = reverse('utilisateur:utilisateur_password', args=[self.cible.pk])
        html = self.client.get(url).content.decode()
        self.assertEqual(html.count('autocomplete="new-password"'), 2)
        self.assertNotIn('value="' + self.MDP_CLIENT, html)
        reponse = self.client.post(url, {'new_password1': 'NouveauMdp!2026', 'new_password2': 'NouveauMdp!2026'})
        self.assertRedirects(reponse, reverse('utilisateur:utilisateur_detail', args=[self.cible.pk]))
        self.cible.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertTrue(self.cible.check_password('NouveauMdp!2026'))
        self.assertTrue(self.admin.check_password(self.MDP_ADMIN))
        self.assertTrue(self.toujours_connecte())

    def test_reinitialisation_erreurs_affichees_et_rien_enregistre(self):
        self.connecter('admin1', self.MDP_ADMIN)
        url = reverse('utilisateur:utilisateur_password', args=[self.cible.pk])
        reponse = self.client.post(url, {'new_password1': 'NouveauMdp!2026', 'new_password2': 'Different!2026'})
        self.assertContains(reponse, 'Les deux mots de passe ne sont pas identiques.')
        reponse = self.client.post(url, {'new_password1': '123', 'new_password2': '123'})
        self.assertContains(reponse, 'field-error')
        self.cible.refresh_from_db()
        self.assertTrue(self.cible.check_password(self.MDP_CLIENT))

    def test_admin_reinitialise_son_propre_mot_de_passe_reste_connecte(self):
        self.connecter('admin1', self.MDP_ADMIN)
        self.client.post(reverse('utilisateur:utilisateur_password', args=[self.admin.pk]),
                         {'new_password1': 'AutreMdp!2026', 'new_password2': 'AutreMdp!2026'})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('AutreMdp!2026'))
        self.assertTrue(self.toujours_connecte())

    def test_reinitialisation_reservee_admin(self):
        self.connecter('cible', self.MDP_CLIENT)
        reponse = self.client.post(reverse('utilisateur:utilisateur_password', args=[self.admin.pk]),
                                   {'new_password1': 'Pirate!2026xx', 'new_password2': 'Pirate!2026xx'})
        self.assertEqual(reponse.status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(self.MDP_ADMIN))

    def test_utilisateur_change_son_propre_mot_de_passe(self):
        self.connecter('cible', self.MDP_CLIENT)
        url = reverse('utilisateur:profil_password')
        html = self.client.get(url).content.decode()
        self.assertEqual(html.count('autocomplete="new-password"'), 2)
        self.assertIn('autocomplete="current-password"', html)
        reponse = self.client.post(url, {'ancien': self.MDP_CLIENT, 'nouveau1': 'MonNouveau!2026',
                                         'nouveau2': 'MonNouveau!2026'})
        self.assertRedirects(reponse, reverse('utilisateur:profil'))
        self.cible.refresh_from_db()
        self.assertTrue(self.cible.check_password('MonNouveau!2026'))
        self.assertTrue(self.toujours_connecte())
        self.assertTrue(User.objects.get(pk=self.admin.pk).check_password(self.MDP_ADMIN))

    def test_mauvais_ancien_mot_de_passe_affiche_l_erreur(self):
        self.connecter('cible', self.MDP_CLIENT)
        reponse = self.client.post(reverse('utilisateur:profil_password'),
                                   {'ancien': 'faux', 'nouveau1': 'MonNouveau!2026', 'nouveau2': 'MonNouveau!2026'})
        self.assertContains(reponse, 'Le mot de passe actuel est incorrect.')
        self.cible.refresh_from_db()
        self.assertTrue(self.cible.check_password(self.MDP_CLIENT))

    def test_utilisateur_modifie_son_profil_seulement(self):
        self.connecter('cible', self.MDP_CLIENT)
        self.client.post(reverse('utilisateur:profil_update'),
                         {'first_name': 'Moi', 'last_name': '', 'email': 'moi@gmail.com'})
        self.cible.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual((self.cible.first_name, self.cible.email), ('Moi', 'moi@gmail.com'))
        self.assertEqual((self.admin.first_name, self.admin.email), ('', 'admin1@gmail.com'))

    def test_formulaires_de_creation_et_connexion(self):
        html = self.client.get(reverse('utilisateur:inscription')).content.decode()
        self.assertEqual(html.count('autocomplete="new-password"'), 2)
        html = self.client.get(reverse('utilisateur:login')).content.decode()
        self.assertIn('autocomplete="current-password"', html)
        self.connecter('admin1', self.MDP_ADMIN)
        html = self.client.get(reverse('utilisateur:utilisateur_create')).content.decode()
        self.assertEqual(html.count('autocomplete="new-password"'), 2)
        self.assertIn('name="username" maxlength="150" autocomplete="off"', html)
        contenu = html.split('<main')[1].split('</main>')[0]
        self.assertNotIn('admin1', contenu)


@unittest.skipUnless(apps.is_installed('Projet_App'), 'projets des amis absents')
class IntegrationEtProtectionsTests(TestCase):
    """Intégration au projet SmartProjects (projets des autres membres) et protections du CRUD."""

    def setUp(self):
        from Projet_App.models import Projet
        self.admin = User.objects.create_user('admin2', 'admin2@gmail.com', 'MotDePasse!123', role='ADMIN')
        self.client_user = User.objects.create_user('cli2', 'cli2@gmail.com', 'MotDePasse!123', role='USER')
        Projet.objects.create(nom='Projet A', proprietaire=self.client_user)
        Projet.objects.create(nom='Projet B', proprietaire=self.client_user)

    def test_admin_ne_peut_pas_se_retirer_ses_droits(self):
        self.client.force_login(self.admin)
        donnees = {'username': 'admin2', 'email': 'admin2@gmail.com', 'role': 'USER', 'is_active': 'on'}
        reponse = self.client.post(reverse('utilisateur:utilisateur_update', args=[self.admin.pk]), donnees)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'Vous ne pouvez pas changer votre propre rôle')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, 'ADMIN')

    def test_admin_ne_peut_pas_se_desactiver(self):
        self.client.force_login(self.admin)
        donnees = {'username': 'admin2', 'email': 'admin2@gmail.com', 'role': 'ADMIN'}   # is_active absent = décoché
        self.client.post(reverse('utilisateur:utilisateur_update', args=[self.admin.pk]), donnees)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_suppression_previent_des_projets(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse('utilisateur:utilisateur_delete', args=[self.client_user.pk]))
        self.assertContains(reponse, '2 projets')
        reponse = self.client.get(reverse('utilisateur:utilisateur_list'))
        self.assertContains(reponse, 'Ses 2 projets seront aussi supprimés')

    def test_suppression_utilisateur_supprime_ses_projets(self):
        from Projet_App.models import Projet
        self.client.force_login(self.admin)
        self.client.post(reverse('utilisateur:utilisateur_delete', args=[self.client_user.pk]))
        self.assertFalse(User.objects.filter(pk=self.client_user.pk).exists())
        self.assertEqual(Projet.objects.count(), 0)

    def test_page_403_pour_un_client_sur_une_page_admin(self):
        self.client.force_login(self.client_user)
        reponse = self.client.get(reverse('utilisateur:utilisateur_list'))
        self.assertContains(reponse, 'Accès refusé', status_code=403)

    def test_tableau_de_bord_client_resume(self):
        self.client.force_login(self.client_user)
        reponse = self.client.get(reverse('utilisateur:dashboard'))
        self.assertEqual(reponse.context['nb_projets'], 2)
        self.assertContains(reponse, 'Choisir un plan')
        self.assertNotContains(reponse, 'FT-0')

    def test_fiche_utilisateur_affiche_les_projets(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse('utilisateur:utilisateur_detail', args=[self.client_user.pk]))
        self.assertEqual(reponse.context['nb_projets'], 2)

    def test_menu_contient_mes_projets_et_pas_de_doublon_dashboard(self):
        self.client.force_login(self.client_user)
        html = self.client.get(reverse('utilisateur:profil')).content.decode()
        self.assertIn('href="%s"' % reverse('projet_list'), html)
        self.assertNotIn('>Tableau de bord</a>', html)

    def test_connexion_redirige_vers_next(self):
        reponse = self.client.post(reverse('utilisateur:login') + '?next=/projets/',
                                   {'username': 'cli2', 'password': 'MotDePasse!123'})
        self.assertRedirects(reponse, '/projets/', fetch_redirect_response=False)

    def test_les_projets_des_autres_restent_prives(self):
        autre = User.objects.create_user('autre', 'autre@gmail.com', 'MotDePasse!123')
        self.client.force_login(autre)
        reponse = self.client.get(reverse('projet_list'))
        self.assertNotContains(reponse, 'Projet A')


class BoutonRetourApresDeconnexionTests(TestCase):
    """Après la déconnexion, la flèche « retour » du navigateur ne doit plus montrer de page connectée."""

    def setUp(self):
        self.user = User.objects.create_user('retour1', 'retour1@gmail.com', 'MotDePasse!123')

    def test_pages_connectees_interdites_au_cache(self):
        self.client.force_login(self.user)
        for nom in ['utilisateur:dashboard', 'utilisateur:profil', 'abonnement:offres']:
            reponse = self.client.get(reverse(nom))
            cache = reponse['Cache-Control']
            self.assertIn('no-store', cache, nom)
            self.assertIn('no-cache', cache, nom)
            self.assertIn('must-revalidate', cache, nom)

    @unittest.skipUnless(apps.is_installed('Projet_App'), 'projets des amis absents')
    def test_pages_des_autres_apps_aussi(self):
        self.client.force_login(self.user)
        self.assertIn('no-store', self.client.get(reverse('projet_list'))['Cache-Control'])

    def test_apres_deconnexion_la_page_redirige_vers_la_connexion(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('utilisateur:dashboard')).status_code, 200)
        self.client.post(reverse('utilisateur:logout'))
        reponse = self.client.get(reverse('utilisateur:dashboard'))
        self.assertRedirects(reponse, reverse('utilisateur:login') + '?next=' + reverse('utilisateur:dashboard'))

    @unittest.skipUnless(apps.is_installed('Compte_App'), 'Compte_App des amis absente')
    def test_deconnexion_par_la_vue_des_amis(self):
        self.client.force_login(self.user)
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('utilisateur:profil')).status_code, 302)

    def test_pages_de_connexion_non_mises_en_cache(self):
        for nom in ['utilisateur:login', 'utilisateur:inscription']:
            self.assertIn('no-store', self.client.get(reverse(nom))['Cache-Control'], nom)

    def test_script_de_rechargement_present(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('utilisateur:dashboard')), 'evenement.persisted')
