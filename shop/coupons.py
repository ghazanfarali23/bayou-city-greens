"""Coupon validation, discount math, and redemption.

Security notes
--------------
* The client only ever submits a *code string*. Every amount is computed
  here, server-side, from the Coupon row — never trusted from the request.
* `validate_coupon()` is used for UI previews (cart/checkout pages).
* `validate_locked_coupon()` runs inside the order-creation transaction on a
  SELECT FOR UPDATE row, so usage limits are enforced atomically and a
  single-use code cannot be double-spent by concurrent checkouts.
* Failed lookups all raise CouponError with a shopper-safe message.
* Apply attempts are rate-limited per session to blunt code guessing.
"""
import time
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from django.utils.crypto import get_random_string

from .models import Coupon, CouponRedemption

SESSION_CODE_KEY = "coupon_code"
SESSION_ATTEMPTS_KEY = "coupon_attempts"

# Brute-force guard: max attempts per rolling window, per session.
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 600

# Alphabet without ambiguous chars (no 0/O, 1/I/L) for generated codes.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class CouponError(Exception):
    """Shopper-safe coupon failure. Message is displayable as-is."""


def normalize_code(raw):
    """Canonical form for storage and lookup: stripped + uppercased."""
    return (raw or "").strip().upper()


def normalize_email(raw):
    return (raw or "").strip().lower()


def generate_code(length=10):
    """Generate an unguessable random code (no ambiguous characters)."""
    return get_random_string(length, CODE_ALPHABET)


def _cents(amount):
    return (Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def get_session_coupon_code(session):
    return normalize_code(session.get(SESSION_CODE_KEY) or "")


def set_session_coupon(session, code):
    session[SESSION_CODE_KEY] = normalize_code(code)
    session.modified = True


def clear_session_coupon(session):
    session.pop(SESSION_CODE_KEY, None)
    session.modified = True


def coupon_attempt_allowed(session):
    """Rolling-window rate limit on code submissions (anti-guessing)."""
    now = time.time()
    attempts = [
        t
        for t in session.get(SESSION_ATTEMPTS_KEY, [])
        if now - t < ATTEMPT_WINDOW_SECONDS
    ]
    session[SESSION_ATTEMPTS_KEY] = attempts
    return len(attempts) < MAX_ATTEMPTS


def record_coupon_attempt(session):
    attempts = session.get(SESSION_ATTEMPTS_KEY, [])
    attempts.append(time.time())
    session[SESSION_ATTEMPTS_KEY] = attempts[-20:]
    session.modified = True


# ---------------------------------------------------------------------------
# Validation + math
# ---------------------------------------------------------------------------
def compute_discount(coupon, cart):
    """Return the discount amount for this cart. Raises CouponError."""
    eligible = Decimal("0")
    for line in cart["items"]:
        product = line["product"]
        if coupon.applies_to_product(product):
            eligible += line["line_total"]
    eligible = _cents(eligible)

    if eligible <= 0:
        raise CouponError("That code doesn't apply to anything in your cart.")
    if eligible < coupon.min_order_subtotal:
        raise CouponError(
            f"That code needs a ${coupon.min_order_subtotal:.2f} order "
            "before it kicks in."
        )

    if coupon.discount_type == "percent":
        discount = eligible * coupon.discount_value / Decimal("100")
        if coupon.max_discount_amount:
            discount = min(discount, coupon.max_discount_amount)
    else:  # fixed
        discount = min(coupon.discount_value, eligible)

    discount = _cents(discount)
    if discount <= 0:
        raise CouponError("That code isn't valid for this order.")
    # Never discount more than the eligible merchandise.
    return min(discount, eligible)


def _check_common(coupon):
    """Checks that don't need the cart. Raises CouponError."""
    now = timezone.now()
    if not coupon.is_active:
        raise CouponError("That code isn't valid.")
    if coupon.valid_from and now < coupon.valid_from:
        raise CouponError("That code isn't active yet.")
    if coupon.valid_to and now > coupon.valid_to:
        raise CouponError("That code has expired.")
    if (
        coupon.usage_limit is not None
        and coupon.usage_count >= coupon.usage_limit
    ):
        raise CouponError("That code has already been fully redeemed.")


def _check_per_customer(coupon, email):
    if coupon.per_customer_limit and email:
        used = CouponRedemption.objects.filter(
            coupon=coupon, email=normalize_email(email)
        ).count()
        if used >= coupon.per_customer_limit:
            raise CouponError("You've already used that code.")


def validate_coupon(raw_code, cart, email=None):
    """Validate a code against the current cart. Returns (coupon, discount).

    Used for UI previews. NOT sufficient for order creation — the order path
    must use validate_locked_coupon() inside a transaction.
    """
    code = normalize_code(raw_code)
    if not code:
        raise CouponError("Enter a coupon code.")
    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        raise CouponError("That code isn't valid.")
    _check_common(coupon)
    _check_per_customer(coupon, email)
    return coupon, compute_discount(coupon, cart)


def validate_locked_coupon(coupon, cart, email=None):
    """Same as validate_coupon, but for an already-locked row.

    Call with the coupon fetched via select_for_update() inside the order
    transaction — this is the security gate that makes usage limits atomic.
    """
    _check_common(coupon)
    _check_per_customer(coupon, email)
    return coupon, compute_discount(coupon, cart)


def redeem_locked_coupon(coupon, order, email, discount):
    """Record a redemption and bump usage_count. Call inside the order txn."""
    coupon.usage_count += 1
    coupon.save(update_fields=["usage_count"])
    CouponRedemption.objects.create(
        coupon=coupon,
        order=order,
        email=normalize_email(email),
        discount_amount=discount,
    )
