from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Purchase, PurchaseItem


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):

    list_display = (
        "invoice_number",
        "supplier",
        "subtotal",
        "created_by",
        "created_at",
    )

    search_fields = (
        "invoice_number",
        "supplier__name",
        "supplier__company",
    )

    list_filter = (
        "supplier",
        "created_at",
    )


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):

    list_display = (
        "purchase",
        "product",
        "quantity",
        "purchase_price",
        "total",
    )

    search_fields = (
        "purchase__invoice_number",
        "product__name",
        "product__code",
    )

