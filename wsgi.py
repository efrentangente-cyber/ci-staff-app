"""
WSGI entrypoint for Gunicorn / Render.

Use: gunicorn --config gunicorn.conf.py wsgi:application

Importing ``application`` loads ``app.py`` (Socket.IO middleware is already
attached to the Flask instance there). Prefer this module name over ``app:app``
so platform defaults and docs have a single, obvious target.
"""
from app import app as application

__all__ = ('application',)
