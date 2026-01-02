"""
SocialAppとSiteの紐付け確認スクリプト
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

# Google SocialAppを取得
try:
    app = SocialApp.objects.get(provider='google')
    print(f"SocialApp: {app.name} (provider={app.provider})")
    print(f"Client ID: {app.client_id[:20]}...")
    print(f"Associated sites: {list(app.sites.all())}")

    # Site ID=1を取得
    site = Site.objects.get(id=1)
    print(f"\nCurrent Site (ID=1): {site.domain} ({site.name})")

    # 紐付けチェック
    if site not in app.sites.all():
        app.sites.add(site)
        print(f"\n✓ Added site: {site.domain}")
    else:
        print(f"\n✓ Already associated with: {site.domain}")

    # 最終確認
    print(f"\nFinal associated sites: {list(app.sites.all())}")

except SocialApp.DoesNotExist:
    print("ERROR: Google SocialApp not found!")
    print("Please create it in Django admin: http://127.0.0.1:8000/admin/socialaccount/socialapp/")
except Exception as e:
    print(f"ERROR: {e}")
