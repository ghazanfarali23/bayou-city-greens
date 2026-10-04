from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("shop/", views.product_list, name="product_list"),
    path("shop/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("coupon/apply/", views.coupon_apply, name="coupon_apply"),
    path("coupon/remove/", views.coupon_remove, name="coupon_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<str:number>/", views.order_confirmation, name="order_confirmation"),
    path("subscribe/weekly-box/", views.subscribe_weekly_box, name="subscribe_weekly_box"),
    path(
        "subscribe/confirmed/",
        views.subscription_confirmation,
        name="subscription_confirmation",
    ),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("deploy/github/", views.github_deploy_webhook, name="github_deploy"),
]
