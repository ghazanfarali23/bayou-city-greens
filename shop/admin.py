from django.contrib import admin

from .models import Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "unit", "category", "is_active", "is_featured", "sort_order")
    list_filter = ("is_active", "is_featured", "category")
    list_editable = ("price", "is_active", "is_featured", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number", "name", "fulfillment", "total", "payment_status", "status", "created",
    )
    list_filter = ("fulfillment", "payment_status", "status", "created")
    search_fields = ("number", "name", "email", "phone")
    readonly_fields = ("number", "subtotal", "delivery_fee", "total", "created", "updated")
    inlines = [OrderItemInline]
    actions = ["mark_preparing", "mark_ready", "mark_completed"]

    @admin.action(description="Mark as preparing")
    def mark_preparing(self, request, queryset):
        queryset.update(status="preparing")

    @admin.action(description="Mark ready for pickup / out for delivery")
    def mark_ready(self, request, queryset):
        queryset.update(status="ready")

    @admin.action(description="Mark completed")
    def mark_completed(self, request, queryset):
        queryset.update(status="completed")
