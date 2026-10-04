"""Session-based cart helpers. Keys are product ids stored as strings."""
from decimal import Decimal

from .models import Product

SESSION_KEY = "cart"


def _raw_cart(session):
    cart = session.get(SESSION_KEY)
    if not isinstance(cart, dict):
        cart = {}
        session[SESSION_KEY] = cart
    return cart


def add_to_cart(session, product_id, quantity=1):
    cart = _raw_cart(session)
    key = str(product_id)
    cart[key] = cart.get(key, 0) + max(1, int(quantity))
    session.modified = True


def set_quantity(session, product_id, quantity):
    cart = _raw_cart(session)
    key = str(product_id)
    quantity = int(quantity)
    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity
    session.modified = True


def remove_from_cart(session, product_id):
    cart = _raw_cart(session)
    cart.pop(str(product_id), None)
    session.modified = True


def clear_cart(session):
    session.pop(SESSION_KEY, None)
    session.modified = True


def cart_count(session):
    return sum(int(q) for q in _raw_cart(session).values())


def cart_details(session):
    """Return items with product objects plus subtotal and count."""
    items = []
    subtotal = Decimal("0")
    for pid, qty in _raw_cart(session).items():
        try:
            product = Product.objects.get(pk=int(pid), is_active=True)
        except (Product.DoesNotExist, ValueError):
            continue
        qty = int(qty)
        line_total = product.price * qty
        items.append(
            {
                "product": product,
                "quantity": qty,
                "line_total": line_total,
            }
        )
        subtotal += line_total
    return {"items": items, "subtotal": subtotal, "count": sum(i["quantity"] for i in items)}
