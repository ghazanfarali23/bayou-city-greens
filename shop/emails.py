"""Transactional emails for Space City Sprouts.

All mail goes out as multipart (plain text + HTML) from the branded
hello@spacecitysprouts.com address via the local Plesk mail server, with
SPF/DKIM/DMARC published in DNS so it stays out of spam folders.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def _send_mail(*, to, subject, template, context, cc=None, reply_to=None):
    """Render both parts and send. Returns True if sent."""
    context = {
        **context,
        "brand_name": settings.BRAND_NAME,
        "site_url": "https://spacecitysprouts.com",
        "contact_email": settings.CONTACT_EMAIL,
        "contact_phone": settings.CONTACT_PHONE,
    }
    text_body = render_to_string(f"emails/{template}.txt", context)
    html_body = render_to_string(f"emails/{template}.html", context)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
        cc=cc or [],
        reply_to=reply_to or [settings.CONTACT_EMAIL],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
    return True


def _order_context(order):
    items = order.items.select_related("product")
    return {
        "order": order,
        "items": items,
        "is_pickup": order.fulfillment == "pickup",
    }


# ---------------------------------------------------------------------------
# One-time orders
# ---------------------------------------------------------------------------
def send_staff_order_notification(order):
    """Notify the grow team about a new order (created or renewal)."""
    to = [settings.STAFF_ORDER_EMAIL]
    cc = [e for e in settings.STAFF_ORDER_CC if e]
    subject = f"🌱 New order {order.number} — {order.get_fulfillment_display()}"
    if "subscription" in (order.notes or "").lower():
        subject = f"🌱 Weekly subscription harvest {order.number}"
    _send_mail(
        to=to,
        cc=cc,
        subject=subject,
        template="order_staff",
        context=_order_context(order),
    )
    order.staff_emailed = True
    order.save(update_fields=["staff_emailed"])


def send_customer_order_confirmation(order):
    """Branded confirmation to the customer."""
    if order.payment_status == "paid":
        subject = f"Order confirmed {order.number} — thank you! 🌱"
    else:
        subject = f"Order received {order.number} — pay on pickup/delivery 🌱"
    _send_mail(
        to=[order.email],
        subject=subject,
        template="order_customer",
        context=_order_context(order),
    )
    order.customer_emailed = True
    order.save(update_fields=["customer_emailed"])


# ---------------------------------------------------------------------------
# Weekly subscriptions
# ---------------------------------------------------------------------------
def _subscription_context(subscription):
    return {
        "subscription": subscription,
        "is_pickup": subscription.fulfillment == "pickup",
    }


def send_staff_subscription_notification(subscription):
    to = [settings.STAFF_ORDER_EMAIL]
    cc = [e for e in settings.STAFF_ORDER_CC if e]
    _send_mail(
        to=to,
        cc=cc,
        subject=f"🔁 New weekly subscription — {subscription.name}",
        template="subscription_staff",
        context=_subscription_context(subscription),
    )
    subscription.staff_emailed = True
    subscription.save(update_fields=["staff_emailed"])


def send_customer_subscription_confirmation(subscription):
    _send_mail(
        to=[subscription.email],
        subject="You're subscribed — Weekly Harvest Box 🌱",
        template="subscription_customer",
        context=_subscription_context(subscription),
    )
    subscription.customer_emailed = True
    subscription.save(update_fields=["customer_emailed"])
