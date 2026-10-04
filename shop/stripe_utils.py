"""Stripe helpers. Only called when STRIPE_SECRET_KEY is configured."""
from django.conf import settings
from django.urls import reverse


def get_or_create_stripe_coupon(order):
    """Return a Stripe coupon id for this order's discount.

    Always created as a fixed-amount (amount_off) coupon for the exact
    computed discount — never as percent_off — so what Stripe charges
    matches the order total to the cent, even with percent caps or
    product-restricted coupons. One coupon per order (duration: once).
    """
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    coupon = stripe.Coupon.create(
        amount_off=int(order.discount_amount * 100),
        currency="usd",
        duration="once",
        name=f"Space City Sprouts {order.number} ({order.coupon_code})",
        metadata={
            "order_number": order.number,
            "coupon_code": order.coupon_code,
        },
    )
    return coupon.id


def create_checkout_session(order, request):
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Discounts attach to product line items only — never the delivery fee
    # line — so Stripe's math matches the order total exactly.
    stripe_coupon_id = None
    if order.coupon and order.discount_amount > 0:
        stripe_coupon_id = get_or_create_stripe_coupon(order)

    def _eligible(product):
        return bool(order.coupon) and order.coupon.applies_to_product(product)

    line_items = []
    for item in order.items.all():
        line = {
            "price_data": {
                "currency": "usd",
                "unit_amount": int(item.unit_price * 100),
                "product_data": {
                    "name": f"{item.product.name} — {item.product.unit}",
                },
            },
            "quantity": item.quantity,
        }
        if stripe_coupon_id and _eligible(item.product):
            line["discounts"] = [{"coupon": stripe_coupon_id}]
        line_items.append(line)
    if order.delivery_fee > 0:
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(order.delivery_fee * 100),
                    "product_data": {"name": "Local delivery (Houston area)"},
                },
                "quantity": 1,
            }
        )

    success_url = (
        request.build_absolute_uri(
            reverse("order_confirmation", args=[order.number])
        )
        + "?paid=1"
    )
    cancel_url = request.build_absolute_uri(reverse("checkout"))

    return stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        customer_email=order.email,
        metadata={"order_number": order.number},
    )


def event_from_request(request):
    """Verify the webhook signature and return the Stripe event."""
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    if settings.STRIPE_WEBHOOK_SECRET:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    import json

    return stripe.Event.construct_from(json.loads(payload), stripe.api_key)


def create_subscription_checkout_session(data, request):
    """Create a Stripe Checkout Session in subscription mode for the weekly box."""
    import stripe

    from shop.models import Product

    stripe.api_key = settings.STRIPE_SECRET_KEY
    product = Product.objects.get(slug="weekly-harvest-box")
    if not product.stripe_price_id:
        raise ValueError("Weekly box is missing its Stripe price link.")

    success_url = (
        request.build_absolute_uri(reverse("subscription_confirmation"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = request.build_absolute_uri(reverse("subscribe_weekly_box"))

    return stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": product.stripe_price_id, "quantity": 1}],
        customer_email=data["email"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "kind": "weekly_subscription",
            "name": data["name"],
            "phone": data.get("phone", ""),
            "fulfillment": data.get("fulfillment", "pickup"),
            "address_line1": data.get("address_line1", ""),
            "address_line2": data.get("address_line2", ""),
            "city": data.get("city", ""),
            "zip_code": data.get("zip_code", ""),
        },
    )
