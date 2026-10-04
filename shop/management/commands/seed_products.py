"""Seed the shop with the launch product catalog. Safe to re-run."""
from decimal import Decimal

from django.core.management.base import BaseCommand

from shop.models import Product

PRODUCTS = [
    {
        "name": "Broccoli",
        "slug": "broccoli",
        "tagline": "The nutrition powerhouse — mild, fresh, and endlessly versatile.",
        "description": (
            "Our most popular green. Broccoli microgreens have a mild, fresh flavor "
            "that works on everything from salads and sandwiches to smoothies. "
            "Cut fresh the morning of your pickup or delivery."
        ),
        "nutrition": "Rich in vitamins A, C, and K, plus sulforaphane — the compound broccoli is famous for.",
        "price": Decimal("8.00"),
        "unit": "2 oz clamshell",
        "category": "Mild",
        "image": "img/products/broccoli.jpg",
        "is_featured": True,
        "sort_order": 1,
    },
    {
        "name": "Sunflower Shoots",
        "slug": "sunflower-shoots",
        "tagline": "Thick, crunchy, and nutty — the crowd favorite.",
        "description": (
            "Sunflower shoots are the heartiest microgreen we grow: thick crunchy "
            "stems with a fresh, nutty, almost lemony flavor. Amazing on their own "
            "as a snack, on tacos, or piled on avocado toast."
        ),
        "nutrition": "High in protein, healthy fats, vitamin E, and zinc for their size.",
        "price": Decimal("9.00"),
        "unit": "2 oz clamshell",
        "category": "Mild",
        "image": "img/products/sunflower.jpg",
        "is_featured": True,
        "sort_order": 2,
    },
    {
        "name": "Pea Shoots",
        "slug": "pea-shoots",
        "tagline": "Sweet, tender tendrils that taste like spring.",
        "description": (
            "Delicate, sweet, and tender with beautiful curling tendrils. Pea shoots "
            "are a chef favorite for garnishing — or just eat them straight from the "
            "box. Kids love them."
        ),
        "nutrition": "Loaded with vitamins A and C, folate, and plant protein.",
        "price": Decimal("9.00"),
        "unit": "2 oz clamshell",
        "category": "Mild",
        "image": "img/products/pea-shoots.jpg",
        "is_featured": True,
        "sort_order": 3,
    },
    {
        "name": "Radish",
        "slug": "radish",
        "tagline": "A peppery kick with stunning color.",
        "description": (
            "Beautiful purple-stemmed radish microgreens with a zesty, peppery bite. "
            "The perfect way to wake up eggs, ramen, grain bowls, and sandwiches."
        ),
        "nutrition": "High in vitamin C and antioxidants; the color comes from anthocyanins.",
        "price": Decimal("8.00"),
        "unit": "2 oz clamshell",
        "category": "Spicy",
        "image": "img/products/radish.jpg",
        "is_featured": False,
        "sort_order": 4,
    },
    {
        "name": "Super Salad Mix",
        "slug": "super-salad-mix",
        "tagline": "Our signature blend — a rainbow in every bite.",
        "description": (
            "Our house blend of broccoli, kale, kohlrabi, and red cabbage microgreens. "
            "Mild and balanced with gorgeous color — the easiest way to upgrade any salad."
        ),
        "nutrition": "A broad spectrum of vitamins A, C, K, and antioxidants from four varieties.",
        "price": Decimal("10.00"),
        "unit": "2 oz clamshell",
        "category": "Mixes",
        "image": "img/products/salad-mix.jpg",
        "is_featured": True,
        "sort_order": 5,
    },
    {
        "name": "Spicy Mix",
        "slug": "spicy-mix",
        "tagline": "Mustard and radish — for people who like it bold.",
        "description": (
            "A fiery blend of mustard and radish microgreens. Adds real heat and "
            "wasabi-like punch to tacos, pho, burgers, and anything that needs waking up."
        ),
        "nutrition": "Mustard greens bring vitamins K and A plus the signature sinus-clearing kick.",
        "price": Decimal("10.00"),
        "unit": "2 oz clamshell",
        "category": "Mixes",
        "image": "img/products/spicy-mix.jpg",
        "is_featured": False,
        "sort_order": 6,
    },
    {
        "name": "Weekly Harvest Box",
        "slug": "weekly-harvest-box",
        "tagline": "Four clamshells, cut fresh every week.",
        "description": (
            "Our best value: four 2 oz clamshells of the week's freshest harvest — "
            "a rotating selection of mild, spicy, and signature mixes. Perfect for "
            "families, meal preppers, and smoothie lovers. Order by Sunday night for "
            "a Tuesday harvest."
        ),
        "nutrition": "A full week of concentrated greens nutrition across 4+ varieties.",
        "price": Decimal("29.00"),
        "unit": "4 x 2 oz clamshells",
        "category": "Bundles",
        "image": "img/products/harvest-box.jpg",
        "is_featured": True,
        "sort_order": 7,
    },
]


class Command(BaseCommand):
    help = "Seed the product catalog (idempotent)."

    def handle(self, *args, **options):
        for data in PRODUCTS:
            Product.objects.update_or_create(slug=data["slug"], defaults=data)
            self.stdout.write(self.style.SUCCESS(f"Seeded {data['name']}"))
