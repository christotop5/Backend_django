#!/usr/bin/env bash
# Native Render build (non-Docker). Prefer Dockerfile for GeoDjango.
set -euo pipefail

pip install -r requirements.txt
python manage.py collectstatic --noinput
