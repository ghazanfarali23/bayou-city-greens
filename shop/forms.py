from django import forms
from django.conf import settings

import datetime

HARVEST_LEAD_DAYS = 7


class CheckoutForm(forms.Form):
    FULFILLMENT_CHOICES = [
        ("pickup", "Pickup — free"),
        ("delivery", "Local delivery"),
    ]

    name = forms.CharField(max_length=120, label="Full name")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(max_length=40, label="Phone")
    fulfillment = forms.ChoiceField(
        choices=FULFILLMENT_CHOICES,
        widget=forms.RadioSelect,
        initial="pickup",
        label="How do you want your greens?",
    )
    address_line1 = forms.CharField(
        max_length=200, required=False, label="Street address"
    )
    address_line2 = forms.CharField(
        max_length=200, required=False, label="Apt / suite (optional)"
    )
    city = forms.CharField(max_length=100, required=False)
    zip_code = forms.CharField(max_length=10, required=False, label="ZIP code")
    delivery_date = forms.DateField(
        required=False,
        label="Preferred pickup / delivery day",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="We harvest to order — pick a day at least 7 days out.",
    )
    notes = forms.CharField(
        required=False,
        label="Notes (optional)",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_delivery_date(self):
        date = self.cleaned_data.get("delivery_date")
        if date:
            min_date = datetime.date.today() + datetime.timedelta(
                days=HARVEST_LEAD_DAYS
            )
            if date < min_date:
                raise forms.ValidationError(
                    "Please pick a day at least 7 days out — we harvest to order."
                )
        return date

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("fulfillment") == "delivery":
            for field in ("address_line1", "city", "zip_code"):
                if not cleaned.get(field):
                    self.add_error(field, "Required for local delivery.")
            zip_code = (cleaned.get("zip_code") or "").strip()
            if zip_code and zip_code not in settings.DELIVERY_ZIPS:
                self.add_error(
                    "zip_code",
                    "Sorry — we don't deliver to this ZIP yet. "
                    "Choose pickup, or contact us about your area.",
                )
        return cleaned


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))
