# 公開前・運用開始後タスク整理

最終更新: 2026-06-19

## 公開前に潰すべき課題

| 優先 | 課題 | 状態 | 次の確認 |
| --- | --- | --- | --- |
| S | README認証情報削除 | 対応済み。固定テストパスワードの再混入を `tests.unit.test_release_documentation` で検知 | 公開前にドキュメント検索を再実行 |
| S | Djangoバージョン統一 | Django 5.2.15へ統一済み | 全テスト再実行 |
| S | 権限テスト | キャラシ、HO、GMメモの他人閲覧不可を対象テストで確認済み | 公開前に全権限テストを再実行 |
| A | OAuth設定確認 | ローカルでは設定状態表示のみE2E化済み | Stg/ProdのGoogle、Discord、X callbackを実認可で確認 |
| A | 画像アップロード負荷試験 | 1MB/5MB/上限超過、jpg/png/gifを自動テスト化。ローカルHTTP負荷プローブ実行済み | Stg/Prod相当で `tests/performance/image_upload_load.py` を実行 |
| A | バックアップ手順作成 | `docs/backup.md` 作成済み | 本番AWS値で復旧リハーサル |

### OAuth Stg / Prod確認

実Client ID、Secret、callbackの実値はリポジトリからは確認できません。各Providerの管理画面で次を確認してください。

| Provider | Stg callback | Prod callback | 状態 |
| --- | --- | --- | --- |
| Google | `https://stg.tableno.jp/accounts/google/login/callback/` | `https://tableno.jp/accounts/google/login/callback/` | 未確認 |
| Discord | `https://stg.tableno.jp/accounts/discord/login/callback/` | `https://tableno.jp/accounts/discord/login/callback/` | 未確認 |
| X | `https://stg.tableno.jp/accounts/twitter/login/callback/` | `https://tableno.jp/accounts/twitter/login/callback/` | 未確認 |

### 画像アップロード負荷試験

実HTTPでの同時アップロード確認は以下を使います。

```bash
python tests/performance/image_upload_load.py \
  --base-url http://127.0.0.1:8000 \
  --dev-login admin \
  --concurrency 4 \
  --requests-per-target 9
```

Stg/Prod相当:

```bash
TABLENO_USERNAME=<operator-user> \
TABLENO_PASSWORD=<secret> \
python tests/performance/image_upload_load.py \
  --base-url https://stg.tableno.jp \
  --concurrency 8 \
  --requests-per-target 9
```

| 対象 | サイズ | 形式 | 期待結果 |
| --- | --- | --- | --- |
| キャラ画像 | 1MB | jpg/png/gif | 成功 |
| キャラ画像 | 5MB | jpg/png/gif | 成功または上限境界の明確なエラー |
| キャラ画像 | 上限超過 | jpg/png/gif | 400系、エラーメッセージ表示 |
| シナリオ画像 | 1MB | jpg/png/gif | 成功 |
| シナリオ画像 | 5MB | jpg/png/gif | 成功または上限境界の明確なエラー |
| シナリオ画像 | 上限超過 | jpg/png/gif | 400系、エラーメッセージ表示 |
| 複数枚登録 | 10枚 | jpg/png/gif混在 | 上限内で成功、不正混入時は一括拒否 |
| 大量アクセス | 同時アップロード | jpg/png/gif混在 | worker、DB、S3、Redisが枯渇しない |

## 運用開始後の課題

| 優先 | 課題 | 方針 |
| --- | --- | --- |
| B | 利用ログ収集 | ユーザー数、セッション作成数、キャラシ作成数、離脱率を集計 |
| B | フィードバック導線 | 不具合報告、要望フォームを設置 |
| B | 通知機能改善 | Discord通知とメール通知の運用要件を整理 |

## 将来的な改善

| 優先 | 課題 | 方針 |
| --- | --- | --- |
| C | モデル分割 | 巨大な `CharacterSheet` を core/status/profile などへ段階分割 |
| C | API整備 | ココフォリア、Discord Bot、外部連携向けREST APIを整理 |
| C | 性能改善 | 利用者50人超を目安にRedisキャッシュ、DBインデックス、クエリ最適化 |

## β公開前の重点確認

- Playwright E2E: 新規登録、メールログイン、OAuth設定状態表示、セッション作成/編集/削除、HO作成/配布/閲覧制御、キャラシ作成/編集、CCFOLIA JSON出力を自動確認済み。
- 権限: 他人のキャラシ、HO、GMメモが見えないことを対象テストで確認済み。
- モバイルUI: PlaywrightでiPhone/Android相当のセッション一覧とキャラシ編集を自動確認済み。実機確認は公開前に実施。
- エラーページ: 404、403、500のテンプレートを整備済み。表示と導線は公開前に手動確認。
- 外部依存: OAuth実認可、Stg/Prodでの画像負荷、実機モバイル確認はローカルだけでは完了不可。
