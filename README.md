# 🌱 Space City Sprouts

A marketing + e-commerce website for a Houston home-grown organic microgreens business.
Built with Django — storefront, cart, checkout with local pickup/delivery, and Stripe-ready online payments.

**Live pages:** Home · Shop · Product pages · Cart · Checkout · Order confirmation · About · FAQ · Contact
**Ops:** Django admin for products & orders, Stripe webhook marks orders paid automatically.

## Quick start

```bash
cd bayou-city-greens
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then edit .env with your values
python manage.py migrate
python manage.py seed_products
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000 — admin at http://127.0.0.1:8000/admin/

## Configuration (.env)

| Variable | Purpose |
|---|---|
| `BRAND_NAME` | Business name shown across the site |
| `CONTACT_EMAIL` / `CONTACT_PHONE` | Shown in footer & contact page |
| `PICKUP_ADDRESS` | Shown after a pickup order is placed |
| `DELIVERY_FEE` / `FREE_DELIVERY_MINIMUM` | Delivery pricing (defaults $4.95 / free over $35) |
| `DELIVERY_ZIPS` | Comma-separated ZIPs you deliver to (Houston defaults in `config/settings.py`) |
| `STRIPE_SECRET_KEY` etc. | See "Linking Stripe" below |

## Linking Stripe (when ready)

1. Create a Stripe account at https://dashboard.stripe.com and switch it to **Live mode** when you're ready for real payments (use **Test mode** first).
2. Go to **Developers → API keys** and copy:
   - Publishable key → `STRIPE_PUBLISHABLE_KEY`
   - Secret key → `STRIPE_SECRET_KEY`
3. Go to **Developers → Webhooks → Add endpoint**:
   - URL: `https://your-domain.com/stripe/webhook/`
   - Events: `checkout.session.completed`
   - Copy the **Signing secret** → `STRIPE_WEBHOOK_SECRET`
4. Put all three in `.env` and restart the app.

**How it works:** at checkout the site creates a Stripe Checkout Session and sends the customer to Stripe's hosted payment page. On success Stripe calls the webhook, which marks the order `paid` / `preparing` automatically.

**Before keys are added:** checkout still works — orders are saved as *"Pay on pickup/delivery"* so you can take orders from day one and enable online payments later.

To test with Stripe's test mode, use card `4242 4242 4242 4242` (any future expiry, any CVC).

## Deploying

The app is production-ready via `gunicorn` + WhiteNoise (static files served by the app, no extra setup):

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

It also drops cleanly into **Coolify** (Nixpacks/Dockerfile auto-detects Python): set the env vars from `.env.example` in Coolify's environment section, add a persistent volume for `db.sqlite3` (or switch `DATABASES` to Postgres), and point your domain at it.

### Push-to-deploy (Plesk server)

Pushing to `master` auto-deploys to the Plesk server within seconds:

1. A GitHub webhook (`/deploy/github/`, HMAC-signed with `GITHUB_WEBHOOK_SECRET`) fires on every push to `master`.
2. The app runs `deploy.sh`: `git fetch` + `reset --hard origin/master`, `migrate`, `collectstatic`, then restarts gunicorn (`spacecit` has passwordless sudo for that one restart command only).

To deploy manually over SSH: `su -s /bin/bash spacecit -c /var/www/vhosts/spacecitysprouts.com/app/deploy.sh` — or just run `/var/www/vhosts/spacecitysprouts.com/app/deploy.sh` as root.

## Project layout

```
config/          Django project settings, URLs, WSGI
shop/            The whole business: models, views, cart, Stripe, admin
  models.py      Product, Order, OrderItem
  cart.py        Session cart helpers
  stripe_utils.py Stripe Checkout + webhook verification
  management/commands/seed_products.py   Launch catalog (idempotent)
templates/       All pages (Tailwind CSS via CDN + custom css)
static/img/      Site photography (AI-generated placeholders — swap with real photos anytime)
static/css/      Custom styles
```

## Daily ops

- **Products/prices:** Django admin → Products (or edit `seed_products.py` and re-run).
- **Orders:** Django admin → Orders. Use the actions to move orders Pending → Preparing → Ready → Completed.
- **Brand name:** one setting — `BRAND_NAME` in `.env`.

## Notes

- Photos in `static/img/` are AI-generated placeholders so the site looks complete on day one. Replace them with real photos of your grow room and harvests whenever ready (same filenames = zero code changes).
- The delivery ZIP list in `config/settings.py` covers Greater Houston — trim it to the neighborhoods you actually serve.
