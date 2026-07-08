# Public Release Checklist

公開サービス・ポートフォリオ・共同開発に出す前の最終確認リストです。

## Django / Runtime

- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` 設定済み
- [ ] `CSRF_TRUSTED_ORIGINS` / CORS 確認済み
- [ ] 本番用 `SECRET_KEY` はSecret管理から注入
- [ ] `python manage.py check --deploy` 通過
- [ ] `python manage.py billing_release_gate` 通過

## Authentication / External Services

- [ ] Google OAuth 本番URL確認済み
- [ ] Discord OAuth 本番URL確認済み
- [ ] X OAuth 本番URL確認済み
- [ ] Stripe test mode 検証済み
- [ ] Stripe Checkout は公開条件を満たすまで無効化
- [ ] Sentry / CloudWatch 確認済み

## Security / Privacy

- [ ] `.env`、秘密鍵、DBダンプ、実ログが追跡対象にない
- [ ] 共有リンクの権限制御確認済み
- [ ] 秘匿ハンドアウトの直URL権限確認済み
- [ ] 利用規約 / プライバシーポリシー設置済み
- [ ] 特商法ページと問い合わせ導線確認済み

## UX / Release Evidence

- [ ] スマホ主要画面確認済み
- [ ] PC幅主要画面確認済み
- [ ] README用スクリーンショットを `docs/reports/screenshots/` に追加済み
- [ ] `python -m pytest` 通過
- [ ] E2E主要フロー確認済み
- [ ] GitHub Actions 通過

## Repository Hygiene

- [ ] `node_modules/` が追跡対象にない
- [ ] `.env` が追跡対象にない
- [ ] `*.sqlite3` が追跡対象にない
- [ ] `*secret*` や鍵ファイルが追跡対象にない
- [ ] ルート直下に一時スクリプト・検証レポートが残っていない
- [ ] GitHub Issuesへ未対応課題を登録済み