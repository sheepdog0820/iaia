"""Serve only bundled public font assets on the application's own origin."""

from functools import lru_cache

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.http import Http404
from whitenoise import WhiteNoise
from whitenoise.middleware import WhiteNoiseMiddleware


@lru_cache(maxsize=1)
def _font_files():
    # Register fixed public directories once; request paths never reach the filesystem.
    assets = WhiteNoise(application=None, autorefresh=False, max_age=3600)
    vendor = settings.BASE_DIR / "static" / "vendor"
    for directory in ("fontawesome/6.0.0", "theme-fonts"):
        assets.add_files(vendor / directory, prefix=f"/{directory}/")
    return assets.files


@login_not_required
def public_font(request, font_path):
    asset = _font_files().get(f"/{font_path}")
    if asset is None:
        raise Http404
    return WhiteNoiseMiddleware.serve(asset, request)
