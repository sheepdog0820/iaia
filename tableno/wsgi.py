"""
WSGI config for tableno project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

from django.core.wsgi import get_wsgi_application

from tableno.runtime_env import configure_runtime_environment

configure_runtime_environment()

application = get_wsgi_application()
