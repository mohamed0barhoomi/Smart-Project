from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from UtilisateursApp.models import User

from .models import SubscriptionPlan, UserSubscription


class BaseTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin1', 'admin1@gmail.com', 'MotDePasse!123', role='ADMIN')
        self.client_user = User.objects.create_user('client1', 'client1@gmail.com', 'MotDePasse!123')
        self.plan = SubscriptionPlan.objects.create(name='Pro', price='49.90', duration_days=30)
        self.plan_inactif = SubscriptionPlan.objects.create(name='Ancien', price='10', duration_days=7, is_active=False)


class PlanCrudTests(BaseTest):
    def test_client_interdit(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse('abonnement:plan_list')).status_code, 403)

    def test_anonyme_redirige_vers_connexion(self):
        reponse = self.client.get(reverse('abonnement:plan_list'))
        self.assertRedirects(reponse, reverse('utilisateur:login') + '?next=' + reverse('abonnement:plan_list'))

    def test_liste_et_detail(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse('abonnement:plan_list'))
        self.assertContains(reponse, 'Pro')
        self.assertContains(reponse, 'Ancien')
        self.assertContains(self.client.get(reverse('abonnement:plan_detail', args=[self.plan.pk])), '49.90 DT')

    def test_creation(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse('abonnement:plan_create'), {
            'name': 'Premium', 'price': '99.00', 'duration_days': 90, 'description': 'Tout inclus', 'is_active': 'on'})
        self.assertRedirects(reponse, reverse('abonnement:plan_list'))
        self.assertTrue(SubscriptionPlan.objects.filter(name='Premium', duration_days=90).exists())

    def test_creation_invalide(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse('abonnement:plan_create'), {
            'name': 'pro', 'price': '-5', 'duration_days': 0})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'Un plan porte déjà ce nom.')
        self.assertEqual(SubscriptionPlan.objects.count(), 2)

    def test_modification(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('abonnement:plan_update', args=[self.plan.pk]), {
            'name': 'Pro', 'price': '59.90', 'duration_days': 31, 'description': ''})
        self.plan.refresh_from_db()
        self.assertEqual(str(self.plan.price), '59.90')
        self.assertFalse(self.plan.is_active)  # case décochée

    def test_suppression_avec_confirmation(self):
        self.client.force_login(self.admin)
        url = reverse('abonnement:plan_delete', args=[self.plan_inactif.pk])
        self.assertContains(self.client.get(url), 'Voulez-vous vraiment supprimer')
        self.assertTrue(SubscriptionPlan.objects.filter(pk=self.plan_inactif.pk).exists())
        self.client.post(url)
        self.assertFalse(SubscriptionPlan.objects.filter(pk=self.plan_inactif.pk).exists())

    def test_suppression_bloquee_si_plan_utilise(self):
        UserSubscription.objects.create(user=self.client_user, plan=self.plan)
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse('abonnement:plan_delete', args=[self.plan.pk]))
        self.assertContains(reponse, 'désactivez-le')
        self.assertTrue(SubscriptionPlan.objects.filter(pk=self.plan.pk).exists())


class ExpirationTests(BaseTest):
    def test_abonnement_depasse_devient_expire(self):
        from .models import abonnement_en_cours
        s = UserSubscription.objects.create(user=self.client_user, plan=self.plan, payment_status='PAID',
                                            start_date=date.today() - timedelta(40),
                                            end_date=date.today() - timedelta(10))
        self.assertIsNone(abonnement_en_cours(self.client_user))
        s.refresh_from_db()
        self.assertEqual(s.status, 'EXPIRED')


class ParcoursClientTests(BaseTest):
    CARTE = {'titulaire': 'Client Un', 'numero': '4242 4242 4242 4242', 'expiration': '12/99', 'cvv': '123'}

    def setUp(self):
        super().setUp()
        self.client.force_login(self.client_user)

    def test_carte_dashboard_mene_aux_offres(self):
        self.assertContains(self.client.get(reverse('utilisateur:dashboard')), reverse('abonnement:offres'))

    def test_offres_affiche_seulement_plans_actifs(self):
        reponse = self.client.get(reverse('abonnement:offres'))
        self.assertContains(reponse, 'Pro')
        self.assertNotContains(reponse, 'Ancien')
        self.assertEqual(self.client.get(reverse('abonnement:souscrire', args=[self.plan_inactif.pk])).status_code, 404)

    def test_parcours_complet(self):
        # 1. Souscrire : crée un abonnement en attente de paiement
        reponse = self.client.post(reverse('abonnement:souscrire', args=[self.plan.pk]))
        abonnement = UserSubscription.objects.get(user=self.client_user)
        self.assertRedirects(reponse, reverse('abonnement:paiement', args=[abonnement.pk]))
        self.assertEqual(abonnement.payment_status, 'PENDING')
        self.assertIsNone(abonnement.end_date)

        # 2. Paiement simulé
        reponse = self.client.post(reverse('abonnement:paiement', args=[abonnement.pk]), self.CARTE)
        self.assertRedirects(reponse, reverse('abonnement:mon_abonnement'))
        abonnement.refresh_from_db()
        self.assertEqual(abonnement.payment_status, 'PAID')
        self.assertEqual(abonnement.status, 'ACTIVE')
        self.assertEqual(abonnement.start_date, date.today())
        self.assertEqual(abonnement.end_date, date.today() + timedelta(days=30))

        # 3. Mon abonnement
        reponse = self.client.get(reverse('abonnement:mon_abonnement'))
        self.assertContains(reponse, 'Pro')
        self.assertContains(reponse, 'encore 30 jours')

        # 4. Impossible de souscrire une 2e fois
        self.assertRedirects(self.client.post(reverse('abonnement:souscrire', args=[self.plan.pk])),
                             reverse('abonnement:mon_abonnement'))
        self.assertEqual(UserSubscription.objects.count(), 1)

        # 5. Annulation (avec confirmation)
        self.assertContains(self.client.get(reverse('abonnement:annuler')), 'Voulez-vous vraiment annuler')
        self.client.post(reverse('abonnement:annuler'))
        abonnement.refresh_from_db()
        self.assertEqual(abonnement.status, 'CANCELLED')
        self.assertContains(self.client.get(reverse('abonnement:mon_abonnement')), "aucun abonnement en cours")

    def test_paiement_carte_invalide(self):
        self.client.post(reverse('abonnement:souscrire', args=[self.plan.pk]))
        abonnement = UserSubscription.objects.get(user=self.client_user)
        reponse = self.client.post(reverse('abonnement:paiement', args=[abonnement.pk]),
                                   {'titulaire': 'X', 'numero': '1234', 'expiration': '01/20', 'cvv': '12'})
        self.assertContains(reponse, '16 chiffres')
        self.assertContains(reponse, 'expirée')
        self.assertContains(reponse, '3 chiffres')
        abonnement.refresh_from_db()
        self.assertEqual(abonnement.payment_status, 'PENDING')

    def test_paiement_abonnement_d_un_autre_client_interdit(self):
        autre = User.objects.create_user('client2', 'client2@gmail.com', 'MotDePasse!123')
        abonnement = UserSubscription.objects.create(user=autre, plan=self.plan)
        reponse = self.client.post(reverse('abonnement:paiement', args=[abonnement.pk]), self.CARTE)
        self.assertEqual(reponse.status_code, 404)

    def test_nouveau_choix_remplace_souscription_non_payee(self):
        self.client.post(reverse('abonnement:souscrire', args=[self.plan.pk]))
        autre_plan = SubscriptionPlan.objects.create(name='Basic', price='19', duration_days=15)
        self.client.post(reverse('abonnement:souscrire', args=[autre_plan.pk]))
        self.assertEqual(list(UserSubscription.objects.values_list('plan__name', flat=True)), ['Basic'])


class AdminAbonnementsTests(BaseTest):
    def setUp(self):
        super().setUp()
        autre = User.objects.create_user('client2', 'client2@gmail.com', 'MotDePasse!123')
        UserSubscription.objects.create(user=self.client_user, plan=self.plan, payment_status='PAID',
                                        end_date=date.today() + timedelta(30))
        UserSubscription.objects.create(user=autre, plan=self.plan, payment_status='PENDING')
        UserSubscription.objects.create(user=autre, plan=self.plan, payment_status='PAID', status='CANCELLED',
                                        end_date=date.today() + timedelta(5))

    def test_liste_reservee_admin(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse('abonnement:abonnement_list')).status_code, 403)

    def test_liste_et_filtre(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse('abonnement:abonnement_list'))
        self.assertEqual(len(reponse.context['liste']), 3)
        reponse = self.client.get(reverse('abonnement:abonnement_list') + '?statut=CANCELLED')
        self.assertEqual(len(reponse.context['liste']), 1)

    def test_statistique_abonnements_actifs(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse('utilisateur:dashboard'))
        # Seul l'abonnement actif ET payé compte (pas l'attente de paiement, pas l'annulé)
        self.assertEqual(reponse.context['nb_abonnements_actifs'], 1)
        self.assertContains(reponse, 'Abonnements actifs')
        self.assertContains(reponse, reverse('abonnement:abonnement_list'))


class AdminAbonnementsCrudTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.abonnement = UserSubscription.objects.create(user=self.client_user, plan=self.plan, payment_status='PAID',
                                                          end_date=date.today() + timedelta(30))
        self.client.force_login(self.admin)

    def test_detail(self):
        reponse = self.client.get(reverse('abonnement:abonnement_detail', args=[self.abonnement.pk]))
        self.assertContains(reponse, 'client1')
        self.assertContains(reponse, 'Pro')

    def test_modification_statut(self):
        url = reverse('abonnement:abonnement_update', args=[self.abonnement.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        reponse = self.client.post(url, {'status': 'CANCELLED'})
        self.assertRedirects(reponse, reverse('abonnement:abonnement_detail', args=[self.abonnement.pk]))
        self.abonnement.refresh_from_db()
        self.assertEqual(self.abonnement.status, 'CANCELLED')

    def test_modification_statut_invalide(self):
        reponse = self.client.post(reverse('abonnement:abonnement_update', args=[self.abonnement.pk]), {'status': 'XXX'})
        self.assertEqual(reponse.status_code, 200)
        self.abonnement.refresh_from_db()
        self.assertEqual(self.abonnement.status, 'ACTIVE')

    def test_suppression_avec_confirmation(self):
        url = reverse('abonnement:abonnement_delete', args=[self.abonnement.pk])
        self.assertContains(self.client.get(url), 'Voulez-vous vraiment supprimer')
        self.assertTrue(UserSubscription.objects.filter(pk=self.abonnement.pk).exists())
        self.assertRedirects(self.client.post(url), reverse('abonnement:abonnement_list'))
        self.assertFalse(UserSubscription.objects.filter(pk=self.abonnement.pk).exists())

    def test_reserve_admin(self):
        self.client.force_login(self.client_user)
        for nom in ['abonnement_detail', 'abonnement_update', 'abonnement_delete']:
            self.assertEqual(self.client.get(reverse(f'abonnement:{nom}', args=[self.abonnement.pk])).status_code, 403)


class PaiementTests(BaseTest):
    def setUp(self):
        super().setUp()
        from .models import Paiement
        self.abonnement = UserSubscription.objects.create(user=self.client_user, plan=self.plan, payment_status='PAID',
                                                          end_date=date.today() + timedelta(30))
        Paiement.objects.create(subscription=self.abonnement, amount='49.90', status='PAID')
        Paiement.objects.create(subscription=self.abonnement, amount='49.90', status='FAILED')
        Paiement.objects.create(subscription=self.abonnement, amount='10.00', method='VIREMENT', status='PENDING')

    def test_revenus_du_mois_compte_seulement_les_paiements_payes(self):
        from decimal import Decimal
        from .models import revenus_du_mois
        self.assertEqual(revenus_du_mois(), Decimal('49.90'))

    def test_liste_et_filtre_admin(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse('abonnement:paiement_list'))
        self.assertEqual(len(reponse.context['liste']), 3)
        self.assertContains(reponse, 'Virement')
        reponse = self.client.get(reverse('abonnement:paiement_list') + '?statut=FAILED')
        self.assertEqual(len(reponse.context['liste']), 1)
        self.assertContains(reponse, 'badge-danger')

    def test_liste_reservee_admin(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse('abonnement:paiement_list')).status_code, 403)

    def test_paiements_dans_detail_abonnement(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse('abonnement:abonnement_detail', args=[self.abonnement.pk]))
        self.assertEqual(len(reponse.context['paiements']), 3)

    def test_suppression_abonnement_supprime_ses_paiements(self):
        from .models import Paiement
        self.abonnement.delete()
        self.assertEqual(Paiement.objects.count(), 0)


class ParcoursPaiementTests(BaseTest):
    CARTE = {'titulaire': 'Client Un', 'numero': '4242 4242 4242 4242', 'expiration': '12/99', 'cvv': '123'}
    CARTE_REFUSEE = {'titulaire': 'Client Un', 'numero': '4000 0000 0000 0002', 'expiration': '12/99', 'cvv': '123'}

    def setUp(self):
        super().setUp()
        self.basic = SubscriptionPlan.objects.create(name='Basic', price='19.00', duration_days=15)
        self.client.force_login(self.client_user)

    def souscrire_et_payer(self, plan, carte):
        self.client.post(reverse('abonnement:souscrire', args=[plan.pk]))
        abonnement = UserSubscription.objects.get(user=self.client_user, payment_status='PENDING')
        return abonnement, self.client.post(reverse('abonnement:paiement', args=[abonnement.pk]), carte)

    def test_page_plans_en_cartes(self):
        reponse = self.client.get(reverse('abonnement:offres'))
        self.assertContains(reponse, 'plan-card', count=2)
        self.assertContains(reponse, 'Choisir', count=2)
        self.assertContains(reponse, '49.90 DT')

    def test_paiement_accepte_cree_un_paiement_paye(self):
        from .models import Paiement
        abonnement, reponse = self.souscrire_et_payer(self.plan, self.CARTE)
        self.assertRedirects(reponse, reverse('abonnement:mon_abonnement'))
        paiement = Paiement.objects.get()
        self.assertEqual((paiement.status, paiement.method, str(paiement.amount)), ('PAID', 'CARTE', '49.90'))
        abonnement.refresh_from_db()
        self.assertEqual((abonnement.status, abonnement.payment_status), ('ACTIVE', 'PAID'))

    def test_carte_refusee_cree_un_paiement_echoue(self):
        from .models import Paiement
        abonnement, reponse = self.souscrire_et_payer(self.plan, self.CARTE_REFUSEE)
        self.assertContains(reponse, 'Paiement refusé')
        self.assertEqual(Paiement.objects.get().status, 'FAILED')
        abonnement.refresh_from_db()
        self.assertEqual(abonnement.payment_status, 'PENDING')

    def test_changement_de_plan(self):
        ancien, _ = self.souscrire_et_payer(self.plan, self.CARTE)
        reponse = self.client.get(reverse('abonnement:souscrire', args=[self.basic.pk]))
        self.assertContains(reponse, 'remplacera votre plan actuel')
        nouveau, reponse = self.souscrire_et_payer(self.basic, self.CARTE)
        self.assertRedirects(reponse, reverse('abonnement:mon_abonnement'))
        ancien.refresh_from_db()
        nouveau.refresh_from_db()
        self.assertEqual(ancien.status, 'CANCELLED')
        self.assertEqual((nouveau.status, nouveau.payment_status), ('ACTIVE', 'PAID'))
        reponse = self.client.get(reverse('abonnement:mon_abonnement'))
        self.assertEqual(reponse.context['abonnement'], nouveau)
        self.assertEqual(len(reponse.context['historique']), 1)
        self.assertEqual(len(reponse.context['paiements']), 2)

    def test_changement_en_attente_garde_le_plan_actuel(self):
        ancien, _ = self.souscrire_et_payer(self.plan, self.CARTE)
        self.client.post(reverse('abonnement:souscrire', args=[self.basic.pk]))
        reponse = self.client.get(reverse('abonnement:mon_abonnement'))
        self.assertEqual(reponse.context['abonnement'], ancien)
        self.assertEqual(reponse.context['en_attente'].plan, self.basic)
        self.assertContains(reponse, 'Finaliser le paiement')

    def test_meme_plan_refuse(self):
        self.souscrire_et_payer(self.plan, self.CARTE)
        reponse = self.client.post(reverse('abonnement:souscrire', args=[self.plan.pk]))
        self.assertRedirects(reponse, reverse('abonnement:mon_abonnement'))
        self.assertEqual(UserSubscription.objects.count(), 1)
