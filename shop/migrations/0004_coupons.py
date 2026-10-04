# Generated for the coupon system: Coupon, CouponRedemption, and
# Order.coupon / Order.coupon_code / Order.discount_amount.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0003_email_flags"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Coupon",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Uppercase letters/numbers. Leave blank to auto-generate a secure random code.",
                        max_length=32,
                        unique=True,
                    ),
                ),
                (
                    "discount_type",
                    models.CharField(
                        choices=[
                            ("percent", "Percent off"),
                            ("fixed", "Fixed amount off"),
                        ],
                        default="percent",
                        max_length=10,
                    ),
                ),
                (
                    "discount_value",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Percent (e.g. 15 = 15%) or fixed dollars (e.g. 5 = $5 off).",
                        max_digits=7,
                    ),
                ),
                (
                    "max_discount_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Optional cap for percent coupons (e.g. 20% off up to $10).",
                        max_digits=7,
                        null=True,
                    ),
                ),
                (
                    "min_order_subtotal",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Minimum merchandise subtotal (before discount) required.",
                        max_digits=7,
                    ),
                ),
                (
                    "usage_limit",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Total times this code can be redeemed. Blank = unlimited.",
                        null=True,
                    ),
                ),
                (
                    "usage_count",
                    models.PositiveIntegerField(
                        default=0,
                        editable=False,
                        help_text="Incremented atomically on each redemption.",
                    ),
                ),
                (
                    "per_customer_limit",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Max redemptions per customer email. Blank = unlimited.",
                        null=True,
                    ),
                ),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_to", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "stripe_coupon_id",
                    models.CharField(blank=True, editable=False, max_length=120),
                ),
                (
                    "notes",
                    models.CharField(
                        blank=True,
                        help_text="Internal note, e.g. 'Instagram launch promo'.",
                        max_length=200,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "products",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Restrict to these products. Blank = all products.",
                        to="shop.product",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CouponRedemption",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "email",
                    models.EmailField(help_text="Customer email, lowercased."),
                ),
                (
                    "discount_amount",
                    models.DecimalField(decimal_places=2, max_digits=7),
                ),
                ("redeemed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "coupon",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="redemptions",
                        to="shop.coupon",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coupon_redemptions",
                        to="shop.order",
                    ),
                ),
            ],
            options={
                "ordering": ["-redeemed_at"],
            },
        ),
        migrations.AddField(
            model_name="order",
            name="coupon",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to="shop.coupon",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="coupon_code",
            field=models.CharField(
                blank=True,
                help_text="Snapshot of the code used, kept even if the coupon is deleted.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="discount_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Discount from a coupon, computed server-side.",
                max_digits=7,
            ),
        ),
    ]
