from django.conf import settings

from .cart import cart_count


def brand(request):
    return {
        "brand_name": settings.BRAND_NAME,
        "brand_tagline": settings.BRAND_TAGLINE,
        "contact_email": settings.CONTACT_EMAIL,
        "contact_phone": settings.CONTACT_PHONE,
        "pickup_address": settings.PICKUP_ADDRESS,
        "service_area": settings.SERVICE_AREA_LABEL,
        "stripe_enabled": bool(settings.STRIPE_SECRET_KEY),
    }


def cart_summary(request):
    return {"cart_count": cart_count(request.session)}
