from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class SubscriptionPlan(models.Model):
    name = models.CharField("nom", max_length=100, unique=True)
    price = models.DecimalField("prix (DT)", max_digits=8, decimal_places=2,
                                validators=[MinValueValidator(0)])
    duration_days = models.PositiveIntegerField("durée (jours)", validators=[MinValueValidator(1)])
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("proposé aux clients", default=True)

    class Meta:
        verbose_name = "plan d'abonnement"
        verbose_name_plural = "plans d'abonnement"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} ({self.price} DT / {self.duration_days} j)"


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Actif"),
        ("EXPIRED", "Expiré"),
        ("CANCELLED", "Annulé"),
    ]
    PAYMENT_CHOICES = [
        ("PENDING", "En attente"),
        ("PAID", "Payé"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="abonnements", verbose_name="client")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT,
                             related_name="abonnements", verbose_name="plan")
    start_date = models.DateField("date de début", default=date.today)
    end_date = models.DateField("date de fin", null=True, blank=True)
    status = models.CharField("statut", max_length=10, choices=STATUS_CHOICES, default="ACTIVE")
    payment_status = models.CharField("paiement", max_length=10, choices=PAYMENT_CHOICES, default="PENDING")
    created_at = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "abonnement"
        verbose_name_plural = "abonnements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.get_status_display()})"


class Paiement(models.Model):
    METHOD_CHOICES = [
        ("CARTE", "Carte bancaire"),
        ("VIREMENT", "Virement"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "En attente"),
        ("PAID", "Payé"),
        ("FAILED", "Échoué"),
    ]

    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE,
                                     related_name="paiements", verbose_name="abonnement")
    amount = models.DecimalField("montant (DT)", max_digits=8, decimal_places=2,
                                 validators=[MinValueValidator(0)])
    date = models.DateTimeField("date", default=timezone.now)
    method = models.CharField("méthode", max_length=10, choices=METHOD_CHOICES, default="CARTE")
    status = models.CharField("statut", max_length=10, choices=STATUS_CHOICES, default="PENDING")

    class Meta:
        verbose_name = "paiement"
        verbose_name_plural = "paiements"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.amount} DT - {self.subscription.user.username} ({self.get_status_display()})"


def mettre_a_jour_expirations():
    UserSubscription.objects.filter(status="ACTIVE", end_date__lt=date.today()).update(status="EXPIRED")


def nb_abonnements_actifs():
    mettre_a_jour_expirations()
    return UserSubscription.objects.filter(status="ACTIVE", payment_status="PAID").count()


def revenus_du_mois():
    maintenant = timezone.localtime()
    total = Paiement.objects.filter(status="PAID", date__year=maintenant.year,
                                    date__month=maintenant.month).aggregate(total=Sum("amount"))["total"]
    return (total or Decimal("0")).quantize(Decimal("0.01"))


def abonnement_en_cours(user):
    mettre_a_jour_expirations()
    return (UserSubscription.objects.filter(user=user, status="ACTIVE").select_related("plan")
            .order_by("payment_status", "-created_at").first())


def changement_en_attente(user):
    en_cours = abonnement_en_cours(user)
    if en_cours is None or en_cours.payment_status != "PAID":
        return None
    return (UserSubscription.objects.filter(user=user, status="ACTIVE", payment_status="PENDING")
            .select_related("plan").first())
