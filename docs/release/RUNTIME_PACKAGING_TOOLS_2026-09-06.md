# ランタイムからのPythonビルドツール除去

通常イメージに残っていたpip・setuptools・wheelと、その内部に同梱された古いライブラリが、[全パッケージ監査](HTTP_CLIENT_VENDOR_2026-09-06.md)で追加6ルールの対象となった。アプリのトップレベルmsgpackは修正版でも、pip内の古いコピーは残っていた。CI用の依存ロックでsetuptoolsを更新しても、通常イメージには反映されなかった。

Dockerfileで固定依存の導入後にpip checkを実行し、成功した場合だけpip・setuptools・wheelをuninstallする。pip自身の導入にもno-cache-dirを指定する。アプリコード・依存ロック・DBスキーマは変更しない。ビルド工程で必要なツールは利用し、最終ランタイムには残さない。OSのコンパイラー等は今回の変更対象ではない。

## 必要性と検証

- アプリ領域とentrypointにpip/setuptools/wheel/pkg_resourcesの直接利用は見当たらず、候補のインストール済みメタデータにも有効な必須依存としての指定はなかった。これは動作検証の代替ではない。
- ツール不在を要求する実行プローブは元イメージでpip存在のため失敗。除去した試作イメージでは不在を確認できた。ドライバー名を誤ってpsycopg2として一度失敗したため、ロックと照合してpsycopgへ修正して再検証した。
- Django、Daphne、Celery、channels_redis、psycopg、MySQLdb、Pillow、rembg、onnxruntime、Stripeのimportが成功。画像透過モデルの実推論・外部サービスとの通信を示す検査ではない。
- 試作イメージで課金・6版版管理・複数画像のDjangoテスト226件成功（54.29秒）。本体Dockerfileへ反映後の通常ビルドでも同じ226件成功（67.60秒）。使い捨てSQLiteを使用し、通信はnetwork none。
- 既存Docker設定テスト22件成功。変更前の不在プローブ失敗、変更後のimport成功、通常ビルドのpip check成功を含め、単にスキャナーの表示だけで判断していない。

## 通常ビルドと本番設定

検証用ソースはa10042faのgit archiveに今回のDockerfileを重ねたもの。コミット前の内容であり、単一のGit SHAだけで表さない。タグtableno-runtime-tools:validation、ID `sha256:3787a1f1c4f80d19914f8e561392d6a15dab0fe8da990fddaa9d1e1c04aa368f`。最終USERはtableno。

専用internalネットワークの空PostgreSQL 16/Redis 7、公開ポートなし、APP_ENV=aws-prod、S3/Checkout無効、隔離用仮値で通常entrypointを起動。移行・collectstatic・ASGI起動が成功し、readiness/登録画面200、静的6件とvendor9件のハッシュ付き配信・CSS/JS gzip内容照合に成功した。check --deployは指摘0、migrate --check成功。release_database_preflightも終了0。DBは空の専用検証用であり、共有データの移行実証ではない。

最終イメージでもpip/setuptools/wheel/pkg_resourcesの不在と上記アプリ依存のimport成功を確認した。pip checkは除去前のビルド中に成功している。除去後のコンテナではpip check自体を実行できないため、以前の実行手順をそのまま合格扱いにしない。

## 監査結果と残リスク

Docker Scout 1.24.0、専用キャッシュ、パッケージ種別の除外なしで357パッケージを索引した。25パッケージ119ルールから20パッケージ113ルールとなり、追加6ルール（CVE-2025-47273、CVE-2026-23949、CVE-2026-24049、CVE-2026-57585、CVE-2026-59890、GHSA-6v7p-g79w-8964）は検出されなくなった。残るルールのpurlはすべてdebで、High 1・Medium 1・Low 105・Unspecified 6、終了2。OS監査の未解決事項は維持する。

スキャナーは一時イメージアーカイブの削除で使用中警告を出したが、索引とSARIF生成は完了した。他のプロセスを停止したり、共有キャッシュを削除したりしていない。

ローカル証跡: tmp/runtime-tools-probe-build.log、tmp/runtime-tools-django-tests.log、tmp/runtime-tools-final-build.log、tmp/runtime-tools-final-tests.log、tmp/runtime-tools-docker-config.log、tmp/runtime-tools-final-http.log、tmp/runtime-tools-final-startup.log、tmp/runtime-tools-final-db.json、tmp/runtime-tools-final.sarif.json、tmp/runtime-tools-final-scout.log。専用アプリ/DB/Redisとネットワークは削除済み。検証イメージと監査証跡は保持する。

変更したDockerfile・セットアップ手順・本記録を差分、UTF-8/LF、日本語文書の観点で確認した。運用上は依存更新時に再ビルドが必要となる。問題があれば本変更単位をrevertできるが、監査指摘のある同梱ライブラリも戻るため、対象機能を確認して復旧を判断する。共有環境、Secrets、課金、実データへの操作は行っていない。

## 別件のCI不安定性

Axios同梱版7ffd1f97のCIはバックエンドなど4ジョブ成功、ブラウザは179 passed / 1 flakyで失敗した。WebKitのゲスト参加・通常登録による引き継ぎケースで、ゲスト側signupのクリック後にPOSTが発生せず30秒を超過。再試行で成功したが、failOnFlakyTestsにより不合格としている。artifact 9984465650（ZIP SHA-256 `eac9743f9831d6552ec0e2c25f4e5154be204d863d6d82877d6679e3825f9bae`）のトレースを取得済みで、原因は調査中。本変更の検証成功でその失敗を解決済みにしない。
