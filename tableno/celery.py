import os

from celery import Celery

from tableno.runtime_env import configure_runtime_environment

configure_runtime_environment()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")

app = Celery("tableno")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
