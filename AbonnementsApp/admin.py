from django.contrib import admin

from .models import Paiement, SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


class PaiementInline(admin.TabularInline):
    model = Paiement
    extra = 0


@admin.register(UserSubscription)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "start_date", "end_date", "status", "payment_status")
    list_filter = ("status", "payment_status", "plan")
    search_fields = ("user__username", "user__email", "plan__name")
    inlines = [PaiementInline]


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("subscription", "amount", "method", "status", "date")
    list_filter = ("status", "method")
    search_fields = ("subscription__user__username", "subscription__user__email")
    date_hierarchy = "date"
