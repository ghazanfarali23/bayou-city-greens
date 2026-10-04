from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import hashlib
import hmac
import json
import subprocess
from pathlib import Path

from .cart import (
    add_to_cart,
    cart_details,
    clear_cart,
    remove_from_cart,
    set_quantity,
)
from .forms import CheckoutForm, ContactForm, SubscriptionForm
from .models import Order, OrderItem, Product, Subscription
from .stripe_utils import (
    create_checkout_session,
    create_subscription_checkout_session,
    event_from_request,
)


# ---------------------------------------------------------------------------
# Marketing pages
# ---------------------------------------------------------------------------
def home(request):
    featured = Product.objects.filter(is_active=True, is_featured=True)
    return render(request, "home.html", {"featured": featured})


def about(request):
    return render(request, "about.html")


def faq(request):
    return render(request, "faq.html")


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            send_mail(
                subject=f"Website contact from {form.cleaned_data['name']}",
                message=(
                    f"From: {form.cleaned_data['name']} "
                    f"<{form.cleaned_data['email']}>\n\n"
                    f"{form.cleaned_data['message']}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
            )
            messages.success(
                request, "Thanks for reaching out — we'll get back to you soon."
            )
            return redirect("contact")
    else:
        form = ContactForm()
    return render(request, "contact.html", {"form": form})


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------
def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, "shop/product_list.html", {"products": products})


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = (
        Product.objects.filter(is_active=True)
        .exclude(pk=product.pk)[:3]
    )
    return render(
        request, "shop/product_detail.html", {"product": product, "related": related}
    )


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    try:
        quantity = max(1, min(99, int(request.POST.get("quantity", 1))))
    except (TypeError, ValueError):
        quantity = 1
    add_to_cart(request.session, product.pk, quantity)
    messages.success(request, f"Added {product.name} to your cart.")
    return redirect(request.POST.get("next") or reverse("cart_detail"))


def cart_detail(request):
    return render(request, "shop/cart.html", {"cart": cart_details(request.session)})


@require_POST
def cart_update(request):
    for key, value in request.POST.items():
        if key.startswith("qty_"):
            try:
                set_quantity(request.session, int(key[4:]), int(value or 0))
            except (TypeError, ValueError):
                continue
    messages.success(request, "Cart updated.")
    return redirect("cart_detail")


@require_POST
def cart_remove(request, pk):
    remove_from_cart(request.session, pk)
    return redirect("cart_detail")


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------
def _delivery_fee(subtotal, fulfillment):
    if fulfillment != "delivery":
        return settings.DELIVERY_FEE * 0
    if subtotal >= settings.FREE_DELIVERY_MINIMUM:
        return settings.DELIVERY_FEE * 0
    return settings.DELIVERY_FEE


@transaction.atomic
def _create_order(form, cart):
    fulfillment = form.cleaned_data["fulfillment"]
    subtotal = cart["subtotal"]
    delivery_fee = _delivery_fee(subtotal, fulfillment)
    order = Order.objects.create(
        name=form.cleaned_data["name"],
        email=form.cleaned_data["email"],
        phone=form.cleaned_data["phone"],
        fulfillment=fulfillment,
        address_line1=form.cleaned_data.get("address_line1", ""),
        address_line2=form.cleaned_data.get("address_line2", ""),
        city=form.cleaned_data.get("city", ""),
        zip_code=form.cleaned_data.get("zip_code", ""),
        delivery_date=form.cleaned_data.get("delivery_date"),
        notes=form.cleaned_data.get("notes", ""),
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=subtotal + delivery_fee,
        payment_status="unpaid",
    )
    for line in cart["items"]:
        OrderItem.objects.create(
            order=order,
            product=line["product"],
            quantity=line["quantity"],
            unit_price=line["product"].price,
        )
    return order


def checkout(request):
    cart = cart_details(request.session)
    if not cart["items"]:
        messages.info(request, "Your cart is empty — pick some greens first.")
        return redirect("product_list")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = _create_order(form, cart)
            clear_cart(request.session)
            if settings.STRIPE_SECRET_KEY:
                session = create_checkout_session(order, request)
                order.stripe_session_id = session.id
                order.save(update_fields=["stripe_session_id"])
                return redirect(session.url)
            order.payment_status = "pay_on_fulfillment"
            order.save(update_fields=["payment_status"])
            return redirect("order_confirmation", number=order.number)
    else:
        form = CheckoutForm()

    preview_fee = _delivery_fee(cart["subtotal"], "delivery")
    return render(
        request,
        "shop/checkout.html",
        {
            "form": form,
            "cart": cart,
            "delivery_fee_amount": settings.DELIVERY_FEE,
            "free_delivery_minimum": settings.FREE_DELIVERY_MINIMUM,
            "preview_fee": preview_fee,
            "stripe_enabled": bool(settings.STRIPE_SECRET_KEY),
        },
    )


def order_confirmation(request, number):
    order = get_object_or_404(Order, number=number)
    just_paid = request.GET.get("paid") == "1" and order.payment_status == "paid"
    return render(
        request,
        "shop/order_confirmation.html",
        {"order": order, "just_paid": just_paid},
    )


# ---------------------------------------------------------------------------
# Weekly box subscription
# ---------------------------------------------------------------------------
def subscribe_weekly_box(request):
    product = get_object_or_404(
        Product, slug="weekly-harvest-box", is_active=True
    )
    stripe_ready = bool(settings.STRIPE_SECRET_KEY) and bool(
        product.stripe_price_id
    )

    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            if not stripe_ready:
                messages.error(
                    request,
                    "Online subscriptions aren't enabled yet — please contact us.",
                )
            else:
                session = create_subscription_checkout_session(
                    form.cleaned_data, request
                )
                return redirect(session.url)
    else:
        form = SubscriptionForm()

    return render(
        request,
        "shop/subscribe.html",
        {
            "form": form,
            "product": product,
            "stripe_ready": stripe_ready,
            "delivery_fee_amount": settings.DELIVERY_FEE,
            "free_delivery_minimum": settings.FREE_DELIVERY_MINIMUM,
        },
    )


def subscription_confirmation(request):
    return render(request, "shop/subscription_confirmation.html")


def _subscription_from_session(obj):
    """Create/update the Subscription record when a subscription checkout completes."""
    meta = obj.get("metadata") or {}
    if meta.get("kind") != "weekly_subscription":
        return None
    sub_id = obj.get("subscription")
    if not sub_id:
        return None
    sub, _ = Subscription.objects.update_or_create(
        stripe_subscription_id=sub_id,
        defaults={
            "name": meta.get("name", ""),
            "email": obj.get("customer_email") or obj.get("customer_details", {}).get("email", ""),
            "phone": meta.get("phone", ""),
            "fulfillment": meta.get("fulfillment", "pickup"),
            "address_line1": meta.get("address_line1", ""),
            "address_line2": meta.get("address_line2", ""),
            "city": meta.get("city", ""),
            "zip_code": meta.get("zip_code", ""),
            "stripe_customer_id": obj.get("customer", ""),
            "status": "active",
        },
    )
    return sub


def _fulfillment_order_for_invoice(invoice):
    """Create a harvest/fulfillment Order for a paid subscription invoice."""
    sub_id = invoice.get("subscription")
    if not sub_id:
        return None
    try:
        sub = Subscription.objects.get(stripe_subscription_id=sub_id)
    except Subscription.DoesNotExist:
        return None
    if sub.status == "canceled":
        return None
    product = Product.objects.filter(slug="weekly-harvest-box").first()
    if not product:
        return None
    # Avoid duplicates if Stripe retries the webhook.
    if Order.objects.filter(
        stripe_session_id=f"in_{invoice.get('id')}", payment_status="paid"
    ).exists():
        return None
    subtotal = product.price
    delivery_fee = _delivery_fee(subtotal, sub.fulfillment)
    order = Order.objects.create(
        name=sub.name,
        email=sub.email,
        phone=sub.phone,
        fulfillment=sub.fulfillment,
        address_line1=sub.address_line1,
        address_line2=sub.address_line2,
        city=sub.city,
        zip_code=sub.zip_code,
        notes="Weekly subscription renewal — harvest per schedule.",
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=subtotal + delivery_fee,
        status="preparing",
        payment_status="paid",
        stripe_session_id=f"in_{invoice.get('id')}",
    )
    OrderItem.objects.create(
        order=order, product=product, quantity=1, unit_price=product.price
    )
    return order


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------
@csrf_exempt
def stripe_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        event = event_from_request(request)
    except Exception:
        return HttpResponse(status=400)

    obj = event["data"]["object"]
    etype = event["type"]

    if etype == "checkout.session.completed":
        if obj.get("mode") == "subscription":
            _subscription_from_session(obj)
        else:
            number = (obj.get("metadata") or {}).get("order_number")
            if number:
                Order.objects.filter(number=number).update(
                    payment_status="paid", status="preparing"
                )
    elif etype == "invoice.paid":
        _fulfillment_order_for_invoice(obj)
    elif etype == "customer.subscription.deleted":
        Subscription.objects.filter(
            stripe_subscription_id=obj.get("id")
        ).update(status="canceled")
    return HttpResponse(status=200)


# ---------------------------------------------------------------------------
# GitHub push-to-deploy webhook
# ---------------------------------------------------------------------------
@csrf_exempt
def github_deploy_webhook(request):
    """Deploy on push to master. Verifies the GitHub HMAC signature, then
    runs deploy.sh in the background so the webhook responds immediately."""
    if request.method != "POST":
        return HttpResponse(status=405)
    secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", "")
    sig = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
    if not secret or not sig:
        return HttpResponse(status=403)
    mac = hmac.new(secret.encode(), request.body, hashlib.sha256)
    if not hmac.compare_digest("sha256=" + mac.hexdigest(), sig):
        return HttpResponse(status=403)
    try:
        payload = json.loads(request.body)
    except Exception:
        return HttpResponse(status=400)
    if payload.get("ref") == "refs/heads/master":
        deploy_sh = Path(settings.BASE_DIR) / "deploy.sh"
        subprocess.Popen(
            ["/bin/bash", str(deploy_sh)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    return HttpResponse(status=200)
