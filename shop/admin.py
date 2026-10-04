from django.contrib import admin

from .coupons import generate_code, normalize_code
from .models import Coupon, CouponRedemption, Order, OrderItem, Product, Subscription


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
        "number", "name", "fulfillment", "coupon_code", "discount_amount",
        "total", "payment_status", "status", "created",
    )
    list_filter = ("fulfillment", "payment_status", "status", "created")
    search_fields = ("number", "name", "email", "phone", "coupon_code")
    readonly_fields = (
        "number", "subtotal", "delivery_fee", "discount_amount",
        "coupon", "coupon_code", "total", "created", "updated",
    )
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


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "name", "email", "fulfillment", "status", "current_period_end", "created",
    )
    list_filter = ("status", "fulfillment", "created")
    search_fields = ("name", "email", "stripe_subscription_id")
    readonly_fields = (
        "stripe_customer_id", "stripe_subscription_id", "created", "updated",
    )


class CouponRedemptionInline(admin.TabularInline):
    model = CouponRedemption
    extra = 0
    can_delete = False
    readonly_fields = ("order", "email", "discount_amount", "redeemed_at")
    fields = ("order", "email", "discount_amount", "redeemed_at")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code", "discount_type", "discount_value", "is_active",
        "usage_count", "usage_limit", "valid_from", "valid_to",
    )
    list_filter = ("is_active", "discount_type", "created_at")
    search_fields = ("code", "notes")
    readonly_fields = ("usage_count", "stripe_coupon_id", "created_at")
    inlines = [CouponRedemptionInline]
    actions = ["generate_secure_codes"]
    fieldsets = (
        (None, {
            "fields": (
                "code", "is_active", "discount_type", "discount_value",
                "max_discount_amount", "notes",
            )
        }),
        ("Restrictions", {
            "fields": (
                "min_order_subtotal", "products", "usage_limit",
                "per_customer_limit", "valid_from", "valid_to",
            )
        }),
        ("Tracking", {
            "fields": ("usage_count", "stripe_coupon_id", "created_at", "created_by"),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Normalize and auto-generate secure codes.
        obj.code = normalize_code(obj.code) or generate_code()
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Generate secure random codes for selected (blank codes only)")
    def generate_secure_codes(self, request, queryset):
        updated = 0
        for coupon in queryset.filter(code=""):
            coupon.code = generate_code()
            coupon.save(update_fields=["code"])
            updated += 1
        self.message_user(request, f"Generated codes for {updated} coupon(s).")


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "order", "email", "discount_amount", "redeemed_at")
    list_filter = ("redeemed_at",)
    search_fields = ("coupon__code", "order__number", "email")
    readonly_fields = ("coupon", "order", "email", "discount_amount", "redeemed_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
