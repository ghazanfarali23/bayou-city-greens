"""Stripe helpers. Only called when STRIPE_SECRET_KEY is configured."""
from django.conf import settings
from django.urls import reverse


def create_checkout_session(order, request):
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    line_items = []
    for item in order.items.all():
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(item.unit_price * 100),
                    "product_data": {
                        "name": f"{item.product.name} — {item.product.unit}",
                    },
                },
                "quantity": item.quantity,
            }
        )
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
