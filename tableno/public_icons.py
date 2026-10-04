"""Serve the site's fixed public icons independently of static CDN storage."""

from functools import lru_cache

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.http import Http404
from whitenoise import WhiteNoise
from whitenoise.middleware import WhiteNoiseMiddleware

ICON_FILES = ("favicon-v1.ico", "favicon-32-v1.png", "apple-touch-icon-v1.png")


@lru_cache(maxsize=1)
def _icon_files():
    assets = WhiteNoise(application=None, autorefresh=False, max_age=3600, mimetypes={".ico": "image/x-icon"})
    assets.add_files(settings.BASE_DIR / "static" / "branding", prefix="/")
    # Request paths only select known public files; they never enter a filesystem join.
    return {name: assets.files[f"/{name}"] for name in ICON_FILES}


@login_not_required
def public_icon(request, icon_path):
    asset = _icon_files().get(icon_path)
    if asset is None:
        raise Http404
    return WhiteNoiseMiddleware.serve(asset, request)
