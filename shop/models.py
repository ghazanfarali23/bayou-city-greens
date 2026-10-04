from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


def generate_order_number():
    return f"SCS-{timezone.now():%Y%m%d}-{get_random_string(6).upper()}"


class Product(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    nutrition = models.TextField(
        blank=True, help_text="Nutrition highlights shown on the product page."
    )
    price = models.DecimalField(max_digits=7, decimal_places=2)
    unit = models.CharField(max_length=60, default="2 oz clamshell")
    category = models.CharField(max_length=60, default="Greens")
    image = models.CharField(
        max_length=200,
        default="img/products/salad-mix.jpg",
        help_text="Path under static/, e.g. img/products/broccoli.jpg",
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    stripe_price_id = models.CharField(
        max_length=120, blank=True, help_text="Optional: link to a Stripe Price."
    )

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Order(models.Model):
    FULFILLMENT_CHOICES = [
        ("pickup", "Pickup"),
        ("delivery", "Local delivery"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("preparing", "Preparing"),
        ("ready", "Ready for pickup / out for delivery"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_CHOICES = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
        ("pay_on_fulfillment", "Pay on pickup/delivery"),
    ]

    number = models.CharField(
        max_length=20, unique=True, default=generate_order_number, editable=False
    )
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    fulfillment = models.CharField(
        max_length=10, choices=FULFILLMENT_CHOICES, default="pickup"
    )
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=9, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    discount_amount = models.DecimalField(
        max_digits=7, decimal_places=2, default=0,
        help_text="Discount from a coupon, computed server-side.",
    )
    coupon = models.ForeignKey(
        "Coupon",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    coupon_code = models.CharField(
        max_length=32,
        blank=True,
        help_text="Snapshot of the code used, kept even if the coupon is deleted.",
    )
    total = models.DecimalField(max_digits=9, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default="unpaid"
    )
    stripe_session_id = models.CharField(max_length=200, blank=True)

    customer_emailed = models.BooleanField(default=False)
    staff_emailed = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Order {self.number}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name="items", on_delete=models.CASCADE
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=7, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Coupon(models.Model):
    """A discount code for one-time orders.

    Security model:
    - Codes are stored normalized (uppercased, stripped) with a DB unique
      constraint; lookups always normalize first.
    - Discounts are ALWAYS computed server-side from this row — the client
      only ever submits the code string, never an amount.
    - Redemption happens inside a transaction with SELECT FOR UPDATE on this
      row, so single-use / limited-use coupons can't be double-spent by
      concurrent checkouts.
    - Every redemption is logged in CouponRedemption (audit trail).
    """

    DISCOUNT_TYPES = [
        ("percent", "Percent off"),
        ("fixed", "Fixed amount off"),
    ]

    code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Uppercase letters/numbers. Leave blank to auto-generate a secure random code.",
    )
    discount_type = models.CharField(
        max_length=10, choices=DISCOUNT_TYPES, default="percent"
    )
    discount_value = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        help_text="Percent (e.g. 15 = 15%) or fixed dollars (e.g. 5 = $5 off).",
    )
    max_discount_amount = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional cap for percent coupons (e.g. 20% off up to $10).",
    )
    min_order_subtotal = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text="Minimum merchandise subtotal (before discount) required.",
    )
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total times this code can be redeemed. Blank = unlimited.",
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Incremented atomically on each redemption.",
    )
    per_customer_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Max redemptions per customer email. Blank = unlimited.",
    )
    products = models.ManyToManyField(
        Product,
        blank=True,
        help_text="Restrict to these products. Blank = all products.",
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    stripe_coupon_id = models.CharField(
        max_length=120, blank=True, editable=False
    )
    notes = models.CharField(
        max_length=200, blank=True, help_text="Internal note, e.g. 'Instagram launch promo'."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def applies_to_product(self, product):
        if not self.products.exists():
            return True
        return self.products.filter(pk=product.pk).exists()


class CouponRedemption(models.Model):
    """Audit log: every coupon use, who used it, on which order, for how much."""

    coupon = models.ForeignKey(
        Coupon, related_name="redemptions", on_delete=models.PROTECT
    )
    order = models.ForeignKey(
        Order, related_name="coupon_redemptions", on_delete=models.CASCADE
    )
    email = models.EmailField(help_text="Customer email, lowercased.")
    discount_amount = models.DecimalField(max_digits=7, decimal_places=2)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-redeemed_at"]

    def __str__(self):
        return f"{self.coupon.code} on {self.order.number}"


class Subscription(models.Model):
    """A recurring weekly harvest-box subscription billed via Stripe."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("past_due", "Past due"),
        ("canceled", "Canceled"),
    ]

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    fulfillment = models.CharField(
        max_length=10, choices=Order.FULFILLMENT_CHOICES, default="pickup"
    )
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    stripe_customer_id = models.CharField(max_length=120, blank=True)
    stripe_subscription_id = models.CharField(max_length=120, unique=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active"
    )
    current_period_end = models.DateTimeField(null=True, blank=True)

    customer_emailed = models.BooleanField(default=False)
    staff_emailed = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Weekly box subscription — {self.name} ({self.status})"
