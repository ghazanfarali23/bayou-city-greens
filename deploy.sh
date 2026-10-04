#!/bin/bash
# Space City Sprouts deploy script.
# Pulls the latest master from GitHub, runs migrations, collects static
# files, and restarts gunicorn. Called by the GitHub push webhook and safe
# to run manually over SSH.
set -euo pipefail

APP=/var/www/vhosts/spacecitysprouts.com/app
cd "$APP"

git fetch origin
git reset --hard origin/master

./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput

sudo -n /usr/bin/systemctl restart spacecitysprouts

echo "deploy done: $(git rev-parse --short HEAD) at $(date -u +%FT%TZ)"
