# リリース候補の依存更新と配布物監査（2026-10-28）

## 対象と公開判断

[Draft PR #7](https://github.com/sheepdog0820/iaia/pull/7) の既知不具合修正に、固定依存と通常Dockerベースの更新を追加する。Python依存の監査不合格を解消するための候補であり、正式公開のNo-Goは維持する。mainマージ、共有DB移行、AWS反映、Secrets/IAM/OAuth変更、課金・外部通知の有効化は実施していない。

更新前 `619757f1` の[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/40597430273)では、Unit / Integrationが2035成功・38省略、行カバレッジ87.45%、Playwrightが228成功した。一方、依存監査は10パッケージ68指摘で失敗した。月末依存テストと固定NodeスクリプトのBandit指摘は同SHAまでに解消している。この旧SHAの成功を、以下の依存更新後のCI成功へ読み替えない。

## 更新内容と理由

| 対象 | 更新前 | 更新後 | 確認事項 |
| --- | --- | --- | --- |
| Python公式Dockerベース | digest `bab1b7ef…` / 実イメージ3.11.17 | index digest `ae952e0a57138a4317b9b61caaa19a8217c2f356803f8d7e63aad08769950937` / linux/amd64 3.11.18 | 公式レジストリーのmanifestと作成日を照合。Debian trixieとPython 3.11系は維持 |
| certifi | 2026.7.22 | 2026.10.19 | 証明書バンドルの既知指摘を解消 |
| Django REST Framework | 3.18.0 | 3.18.2 | API依存の修正。Djangoは5.2.17を維持 |
| msgpack | 1.2.1 | 1.2.3 | Channels/Redisのメッセージ処理を検証 |
| Pillow | 12.3.0 | 13.0.0 | 画像デコード等の既知指摘を解消。Python 3.11以上が必要 |
| rembg | 2.0.81 | 2.0.86 | Pillow 13と両立する公式安定版。明示的なu2net/CPU指定は維持 |
| Twisted | 26.4.0 | **26.10.0rc2** | 上流のセキュリティ修正版候補。正式安定版ではないため、下記の注意事項を伴う |
| 開発用Black | 26.5.1 | 26.10.1 | セキュリティ更新。全599ファイルを変更せずにcheck成功 |
| 開発用filelock | 3.32.4 | 4.2.4 | セキュリティ修正後の安定版 |
| 開発用setuptools | 84.0.0 | 84.1.0 | セキュリティ修正。通常配布イメージでは従来どおり削除 |
| 開発用virtualenv | 21.7.13 | 21.14.10 | 21.14.9の追加指摘も確認し、修正版まで更新 |

`requirements.txt` / `requirements-dev.txt` に最低版と一時固定を記録し、Python 3.11 / pip-tools 7.6.1で3ロックをハッシュ付きで再生成した。実行用は上表の6依存、開発・テスト用は10依存の更新に限定され、新規パッケージの追加・削除や他依存の版変更はない。Stripe SDK・OAuth scope・料金・保存仕様・DBスキーマは変更していない。

Pillowの[公式変更点](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)には、IモードPNG保存と`fromarray()`の一部仕様変更等がある。アプリのRGB/RGBA画像処理と既存モデルの出力を照合した。rembg 2.0.82ではPillow `<13` と衝突したため、無理なインストールや配布物のメタデータ改変は行わず、[2.0.86の公式配布](https://pypi.org/project/rembg/2.0.86/)の `<14` 条件と照合した。

### Twistedのプレリリースを含む点

[PyPIの26.10.0rc2](https://pypi.org/project/Twisted/26.10.0rc2/)は10月27日の公式プレリリースで、調査時の安定版は26.4.0だった。旧版を残すと監査指摘が残るため、候補上でRC2を厳密に固定し、Daphne/HTTP/WebSocket/Redisとの実通信を検証する。

この固定は、プレリリースの未発見不具合をなくす保証ではない。mainマージの承認時にこの点を明示し、正式版が提供されたら同じ互換性試験・監査・通常イメージの再確認を行う。安定版待ちを選ぶ場合は依存更新単位を保留し、修正前の脆弱な版を安全と扱わない。本番反映の承認と兼用しない。

## 隔離検証

- 3ロックの全パッケージのpip-auditは既知指摘0件。ハッシュ付き実インストールのLinux環境でも `pip check` とpip-auditが成功した。CVE除外、監査失敗の無視、依存条件の強制無効化は行っていない。
- 通常DockerfileからPython 3.11.18の候補イメージを構築。テストツールを足した補助イメージと通常配布物は区別する。
- 補助イメージの全体pytestは2028成功・38省略、行カバレッジ87.23%。Git/Chrome不足によるリポジトリ検査の8失敗（subtest含む）・Seleniumの3エラーがあった。Git、Chromium/Driver 156、候補の追跡対象を反映した隔離Git indexを用意し、該当4ファイルを再実行して13テスト・4 subtestがすべて成功した。元の全体実行が成功したという記録には置き換えない。製品コードや検査条件の変更で通過させたものではない。
- 通常イメージ内で、隔離PostgreSQL 18.3の移行・逆移行・再適用、技能、復旧、作成入口、退会案内の33テスト成功。`check --deploy` と `migrate --check` は終了0。
- 通常entrypointのASGIサーバーへ実HTTP/WebSocketで接続し、DB/cache readiness 200、匿名WebSocket 403、合成利用者の認証接続、Redis/msgpackを経由する通知、別利用者への非配送、正常な切断を確認。ASGI Communicatorだけの確認ではない。
- 実u2netモデル、CPU指定、外部通信なしの合成256×256画像で、更新前/後の出力PNG・全RGBA画素のSHA-256が一致した。出力はRGBA、alpha最小0/最大255。1画像の互換性試験であり、全画像の同一性や本番性能の保証ではない。ピークRSSは約1.14 GiBで、既存の専用2 GiBワーカー想定の検証である。Web容量を増強したり、常設ワーカーを作成したりはしていない。
- 初回の実通信用クライアントは検証側のPythonパス不足で失敗した。検証クライアントの`PYTHONPATH`だけを修正して再確認し、失敗ログも保持した。

検証コード、合成設定、モデル比較、実通信ログ、監査JSON/SARIFは専用worktreeのGit管理外 `tmp/` に保持する。実利用者の画像、認証情報、メール配送先は使っていない。

## OS監査と未解決事項

公式[Docker Scout 1.28.0](https://github.com/docker/scout-cli/releases/tag/v1.28.0)を作業用フォルダーへ取得し、公式リリースassetのSHA-256と照合した。既存ツールは置換していない。`cves --format sarif --exit-code local://…` を除外条件なしで実行したところ、候補は292パッケージ中16パッケージに **50指摘（CRITICAL 2 / HIGH 7 / MEDIUM 6 / LOW 35）** が残り、終了2だった。

旧イメージの「Scout 1.5.0、259パッケージ、104指摘」とはツール・ベース・依存が異なる。同じ条件の削減率として比較しない。Python依存についてもScoutだけで安全と判断せず、前述の全ロック・実インストール監査と分けて示す。

| 残る主要指摘 | 実コンポーネントとの照合 | 現在の扱い |
| --- | --- | --- |
| MariaDB由来のCRITICAL 2 / HIGH 6 | 実イメージには `libmariadb3` / `mariadb-common` があり、`mariadbd` / `mysqld` / `mariadb-server` はない。上流の[GIS処理](https://github.com/MariaDB/server/security/advisories/GHSA-8fvj-c57c-pggx)、[FRM解析](https://github.com/MariaDB/server/security/advisories/GHSA-c4gx-34mg-95q5)等はサーバー側の機能 | ソースパッケージ単位の指摘と、クライアントライブラリーの実際の適用を区別して継続レビューする。サーバー不在だけで50指摘すべてを解消済みとは扱わない |
| zlib CVE-2026-85091（HIGH） | 実際のPythonとOSは1.3.1。上流の導入時期は1.3.1.2だが、[Debian Tracker](https://security-tracker.debian.org/tracker/CVE-2026-85091)はtrixieをvulnerableとし、sidの修正版を記載 | 版・コード・ベンダー判定の不一致を未解決として残す。sidのライブラリー混入、独自ネイティブパッチ、検出除外はしない |

OS監査を合格扱いにしていない。新しい通常イメージを本番へ投入する判断、残余リスクの受け入れ、正式公開のGo/No-Goはこの修正の完了と分けて扱う。

## 復旧と承認

作業ブランチへ通常pushし、Draft PRの最終headの[Checks](https://github.com/sheepdog0820/iaia/pull/7/checks)を照合する。更新前のCI成功を最終headの証明に使わない。

依存更新を戻す場合は、Dockerベース・依存宣言・3ロックを同じ修正単位でrevertする。旧依存の監査失敗も戻るため、これを安全性の復旧と扱わない。AWSは一切変更していないため、今回のローカル検証によるAWS切り戻しは不要。

mainマージと開発AWS/0068の承認条件は[候補整理](RELEASE_CANDIDATE_2026-10-28.md)を参照する。共有環境に適用する際は、対象SHAの通常配布物を再構築・照合し、最新の稼働版・非公開バックアップ・復旧手順を確定する。今回の依存更新にDBマイグレーションは追加しない。
