#!/usr/bin/env python3
"""
統計エクスポートAPIの手動確認スクリプト

注意:
- Django の `manage.py test` からは実行されない想定です（テストケース未定義）。
- 手動で実行する場合は `python tests/unit/test_export_manual.py` を使用してください。
"""

from __future__ import annotations

import os


def run() -> int:
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")
    django.setup()

    from django.test import Client
    from accounts.models import CustomUser, Group as CustomGroup, GroupMembership

    client = Client()

    user = CustomUser.objects.create_user(username="testuser_export_manual", password="test123")
    group = CustomGroup.objects.create(name="Test Group 2", created_by=user)
    GroupMembership.objects.create(user=user, group=group, role="admin")

    client.force_login(user)

    response = client.get("/api/accounts/export/statistics/", {"format": "json"})
    print(f"JSON response status: {response.status_code}")

    response = client.get("/api/accounts/export/statistics/", {"format": "csv"})
    print(f"CSV response status: {response.status_code}")
    if response.status_code != 200:
        print(f"CSV response content (head): {response.content[:200]}")

    user.delete()
    group.delete()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

