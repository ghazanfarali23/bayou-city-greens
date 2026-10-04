from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .cart import (
    add_to_cart,
    cart_details,
    clear_cart,
    remove_from_cart,
    set_quantity,
)
from .forms import CheckoutForm, ContactForm
from .models import Order, OrderItem, Product
from .stripe_utils import create_checkout_session, event_from_request


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

    if event["type"] == "checkout.session.completed":
        number = (event["data"]["object"].get("metadata") or {}).get("order_number")
        if number:
            Order.objects.filter(number=number).update(
                payment_status="paid", status="preparing"
            )
    return HttpResponse(status=200)
