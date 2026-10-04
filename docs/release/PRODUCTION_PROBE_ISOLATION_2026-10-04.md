# 本番設定テストの親環境からの独立化（2026-10-04）

## 対象・原因

基点は通常配布物の検証記録 `18e92478`、アプリ候補は `529c30c7770b775f59c9b939f042809058fcd033`。[同候補のCI](https://github.com/sheepdog0820/iaia/actions/runs/37207744357)は全体failureで、Unit / Integrationのproduction設定23件が失敗した（2138 passed/69 skipped）。他5ジョブはsuccess。先行の単独設定33件成功と[通常配布物検証](STRIPE_RAK_RUNTIME_529C30C7_2026-10-04.md)を、CI成功へ拡張しない。

原因はテストのsubprocess fixtureが `APP_ENV=aws-prod` を指定しても、親の `ENVIRONMENT=development` を上書きしていないこと。CIではDjango/Celery初期化が親環境にdevelopmentを設定し、runtime selectorのsetdefaultは既存値を尊重する。したがって本番用live合成キーが非本番判定で拒否され、逆にtestキーを拒否する試験は成功してしまう。明示した親development環境のローカルpytestでも、同じ23 failed/10 passed（23.78秒）を再現した。

修正中には、親のローカルDjango設定モジュールも引き継がれ、ロガー試験が本番でない設定を読む問題を追加で確認した。最初の関連回帰は95 passed/1 failedで、隔離SQLite設定がaws-prod起動を拒否した。期待値や安全な設定制約を緩めず、子プロセスの設定参照も独立化した。

## 修正と承認境界

専用ブランチ `codex/production-probe-environment-isolation-20261004` で、`tests/unit/test_production_settings.py` のテストfixtureのみ修正した。

- 通常の本番probeにENVIRONMENT=production、DJANGO_SETTINGS_MODULE=tableno.settings_production、ENV_FILE空を明示し、親のモード/ローカル設定/envファイルを引き継がない。
- aws-preの既存2fixtureにstagingを明示する。testキーを使う既存試験と、意図したstagingの動作は維持する。
- 個別subprocessの本番fixture3件（必須設定なし/課金設定なし/法定表示プレースホルダー）にもproductionを明示し、前段の別エラーで誤検知しない。
- 親developmentの持越し拒否、本番testキー拒否、設定モジュール/envファイル独立性の新規3試験を追加。subprocessは無効な合成資格情報による設定importだけで、実Stripe/メール/OAuthへ接続しない。

本番アプリのENVIRONMENT解釈、runtime selectorのsetdefault、RAK形式/モード境界、SDK/API版、購入intent/行ロック、Webhook署名、購入開始/メール停止は変更していない。main/AWS/ECR/ECS/共有DB、実キー/Secrets/権限、課金・常設容量/継続費用・実ユーザーデータの変更はない。既存のfavicon/6b6c570c承認を流用しない。元checkoutのハンドアウト未コミット変更は保持する。

## TDD・検証

新規の親development試験2件でREDを確認し、設定モジュール試験1件も追加前のfixtureでREDを確認した。初回GREENのロガー1件失敗は上記の追加隔離で修正し、失敗ログを保持する。

| 検証 | 結果と範囲 |
| --- | --- |
| 親development下の関連pytest | **97 passed、49 subtests passed、4既存警告、28.16秒**。設定36/runtime selector6/RAK16/文書39。DB/実Stripeは使用しない |
| 同じ親環境の設定pytest・coverage | **36 passed、5 subtests passed、4既存警告、28.07秒** |
| 設定テストモジュールcoverage | 209文/6分岐100%。新規3メソッドは11文・分岐0・未実行0。アプリ本体のcoverageではない |
| Black/isort/Flake8 | 変更Python1ファイル成功。全体整形なし |
| Bandit | 終了1、既存productionテストLOW26件、新規0。各指摘行が基点に存在することを照合し、新しい抑制は追加しない |

今回変更はテストと文書だけで、新しいUI表示/実ユーザー向け文言はない。文書更新後の39文書テスト成功、相対リンク欠落0、証跡6件のハッシュ一致、ステージ対象3ファイルのUTF-8/LF/BOM/文字化け・差分検査成功を確認。上の97件と重複する文書39件は合算しない。実差分と日本語記述の自己レビューで追加修正を要する問題は残っていない。共有・実データのDB移行やテストデータ削除は不要。

修正後の全CI・通常配布物はpush後に別途確認する。97件の関連成功を、CI全体の約2200件やOSゲートの合格へ拡張しない。先行配布物のOS39指摘（HIGH3/MEDIUM2/LOW34、Python0）はそのまま未解消。実RAK最小権限/認証、Sandbox/共有Webhook/API版/Secrets切替、共有DB・worker/メール、管理運用方針・外部連携・性能/復旧/事業者運用は未完了で、[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

復旧は今回のテストfixture変更を通常revertするだけで、稼働アプリ/DB/Stripe状態に影響しない。ただし親環境に依存する試験とCI失敗を再導入するため、再現性を評価する。Stripe Tax/automatic_tax・税務登録は変更せず、実運用の販売対象/登録確認は別途必要。

## 保存証跡

保存先 `C:/tmp/iaia-production-probe-isolation-20261004/`。基点の23件再現ログは `C:/tmp/iaia-stripe-runtime-529c30c7/ci-mode-reproduction.log`。生成物はGitへ追加しない。

| 証跡 | SHA-256 |
| --- | --- |
| red.log | 7550d794223e377be2b7787577cfad22d784d9a76e98ce13d7aca32190d7d1c3 |
| red-settings-module.log | eaa462de1156fd11ec77fc989a91bc92d625cb900c431c4e1388a1c086fb25f1 |
| green-final.log | 09a723fa1b70460ac24ba21bdefe0751dad0660af4127b7ad908459e11dc3454 |
| coverage-test.log | 682c7ed6f084d6aecdbb871dd95ce6ca55c10875dbf4317120864f2691ba26b9 |
| coverage.json | 2d040abf3ef816594f97363f15287e382fa422bd188d20aabbd71dc5a00ce119 |
| bandit.json | 58a01c5405acdd8070371c0b43531fbf34ca4c6c3c9a043024393c2f66ce7936 |
