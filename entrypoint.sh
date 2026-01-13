#!/bin/sh

set -e

python manage.py collectstatic --settings=EasyTPCloud.settings.production --noinput

exec gunicorn --bind :8000 --workers 3 EasyTPCloud.wsgi
