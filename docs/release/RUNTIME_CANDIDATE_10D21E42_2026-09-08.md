# 固定候補10d21e42の本番用イメージ検証

## 候補の特定

- ソース: `10d21e4267716a40c0a1b4e32286516f9aa975ec`。未コミット変更のない状態でgit archiveから専用コンテキストを作成。
- archive SHA-256: `9b9d3a9035c7700ae8c598959b2bfe512f92cf90610f251ba789b1a7ac512058`。
- 通常Dockerfileのビルド成功。タグ `tableno-formal-release:10d21e42`、ローカルイメージID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`。
- revisionラベルは上記完全SHA、実行ユーザーはtableno。ECRへは送信しておらず、manifest digestは未取得。
- accounts/api/scenarios/schedules/support/tableno/templates/static内のPython・HTML・JS・CSS計510ファイルがarchiveとSHA-256一致。全OS依存の再現ビルドを証明する照合ではない。

## 通常起動と配信

公開ポートなし・外向き通信なしのinternal Dockerネットワークに専用PostgreSQL 16/Redis 7を作成。APP_ENV=aws-prodで通常entrypointを起動し、空DBへのmigrateとcollectstatic、Daphne起動が成功。静的ファイルは203件コピー・583件後処理。

初回は検証用Stripeキーのsk_test形式が本番設定で拒否され、終了1。検証用の無効なダミー値をsk_live形式に変更して専用アプリを再作成し、上記の成功を確認した。実キーは使わず、Checkout・S3は無効、外部通信も遮断している。本番課金・Stripe実連携の検証ではない。

- readinessと登録画面が200。登録画面の静的ファイル6件を取得。
- vendor9件のハッシュ付きURL配信と、配信本文/静的ファイルの一致を確認。CSS/JSはgzip展開後の一致も確認。
- `check --deploy` 指摘0、`migrate --check` と `release_database_preflight` は終了0。
- 隔離DBはaccounts/0064・schedules/0055適用済み。read_only=true、participantとroleの複合一意制約を確認。共有DBの適用状態を示すものではない。
- pip/setuptools/wheel/pkg_resources不在、Django・Daphne・Celery・channels_redis・psycopg・MySQLdb・Pillow・rembg・onnxruntime・Stripeのimport成功。
- ビルド用4パッケージ不在、libmariadb3/libpq5/libgomp1の保持を確認。

検証後に所有ラベルを照合して専用アプリ・DB・Redis・ネットワークを削除。該当コンテナの残存なしを確認した。イメージは再検査用にローカルへ保持する。

## 証跡と残条件

Docker Scout 1.24.0でこの固定イメージをdeb限定で再監査した。292パッケージを索引し、17パッケージ・48指摘（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）、終了2。以前のcleanイメージのCVE ID集合と一致したが、合格ではない。SARIFは `tmp/release-os-10d21e42.sarif.json`、SHA-256 `b48d57647501ec2a8a60b15cbeb1c4f4abae132a8b4c226c27b8437618254056`。一時イメージアーカイブの削除に使用中警告が出たため、スキャナーキャッシュの削除完了は主張しない。レポートは正常出力され、48件を集計できた。zlib HIGH等の適用条件と緩和策の評価は[OS監査記録](RUNTIME_OS_AUDIT_2026-09-06.md)を引き継ぐ。

Git管理外の証跡: `tmp/release-build-10d21e42.log`、`tmp/release-source-hashes-10d21e42.json`、`tmp/release-runtime-10d21e42-{first-start,startup,http}.log`、`tmp/release-runtime-10d21e42-db.json`。再検証時は固定SHA・イメージIDを照合する。

同候補の[CI](https://github.com/sheepdog0820/iaia/actions/runs/34191048141)は2026-09-08の後続確認でcompleted/success、全5ジョブ成功。GitHubのhead_shaが上記完全SHAであることも照合した。

| ジョブ | 完了ログの結果 |
| --- | --- |
| Unit / Integration（101949012876） | 1745成功・28省略・159警告、844.03秒、総カバレッジ86.87% |
| production-database（101949013136） | 284成功・38サブテスト成功・9警告、80.60秒。報酬APIと同時反映を実行対象に含む |
| playwright（101949013137） | Chromium/Firefox/WebKitの計186成功、12.4分 |
| lint-security（101949013007） | success |
| system（101949012999） | success |

省略や警告を0件と読み替えない。CIのlint-security成功も、別途実行したOS監査の48指摘を解消した意味ではない。以後のソース変更に、この候補のCI成功をそのまま適用しない。

共有環境のマイグレーション・アプリ更新・バックアップ復元検証は未実施。実ストレージ/CDN保護、外部認可/配送、Stripeテスト環境の課金ライフサイクル、公開に必要な事業判断を引き続き揃える。実環境の復旧候補は稼働版とバックアップの再確認が必要で、空DB起動成功だけではロールバック実証にならない。
