# 画像ギャラリー保持と配布物のセキュリティ更新

## 対象・変更理由

開発AWSの `c6226ddb` を基点とする `codex/runtime-security-20261002` に、確認記録とPython依存更新を取り込んだ（`d9e14fb7` / `b3313a91`）。現在のmainへ直接戻すと消える画像ギャラリー関連2コミットを保持する。mainへの追加マージ、ECR push、AWS/共有DBへの変更は行っていない。

`b3313a91` の通常ビルドを `--pull` 付きで作成したところ、OpenSSLは修正版になったがPCRE2は旧版 `10.46-1~deb13u2` のままだった。使い捨てコンテナで `apt-get update` / `apt-cache policy` を実行し、securityリポジトリの候補が `10.46-1~deb13u3` と確認した。[DebianのCVE-2026-103111記録](https://security-tracker.debian.org/tracker/CVE-2026-103111)でも同版が修正版。

Dockerfileを次の範囲で修正した。

- インストール対象に `libpcre2-8-0` を明示し、ベースに既存の旧版があっても更新する。
- Python 3.11 slimのベースを、確認したmulti-platform digest `sha256:bab1b7ef4b450c81002278d035eff85ebe394ae94df904f7a3ba14f7e16e487b` に固定。`--pull` の有無やローカルタグの違いで別のベースを使用しない。aptリポジトリ全体を固定したという意味ではない。
- ベースdigestは今後も新たな脆弱性情報に合わせて明示更新し、再ビルド・監査・回帰検証する。固定したことだけで最新・安全とみなさない。
- 非root実行、不要なビルド依存削除、ハッシュ付きPythonロック、起動時保守の制御は維持する。

## ローカル配布物検証

| 対象 | 結果 |
| --- | --- |
| 初期イメージ | `tableno:runtime-security-20261002`、ID `sha256:e9da1868d9a9e65fd4d8609d8ec4ac8a0f6c2312d8f50977b69c9837965867af`、revision label `b3313a91` |
| 修正後イメージ | `tableno:runtime-security-pinned-20261002`、ID `sha256:388db22dd0057f1721484902179bcd136fd4512e8d69625f56cfc2e8be684841`。Dockerfile/テスト修正を含むローカル検証用ビルドで、AWSへ未投入 |
| 修正後OSライブラリ | PCRE2 `10.46-1~deb13u3`、libssl3t64 `3.5.7-1~deb13u3`、zlib1g `1:1.3.dfsg+really1.3.1-1+b1` |
| Python依存 | oauthlib 4.0.0、PyJWT 2.15.1、urllib3 2.8.0。初期イメージ内で実バージョンを照合 |
| Docker構成テスト | 新規2件は変更前失敗→変更後成功、既存を含め24件成功。Black/isort/Flake8/Bandit成功。利用者向けUI文言の変更なし |
| カバレッジ | 新規8実行行は全到達。テストファイル全体は203行中201行到達（99.01%）。既存の非ASCIIコメント検出の例外分岐2行が未到達で、全ファイル100%を指定した試行は終了1。新規部分100%と区別し、既存分岐は改変しない |
| 通常起動 | 外部通信不可のDocker internal network、公開ポートなし、使い捨てPostgreSQL 18.3/Redis 7で実行。aws-pre設定・通常entrypointのmigrate/collectstatic/Daphne起動成功 |
| マイグレーション | 初期イメージで空の隔離DBへ全移行成功。修正後も同じ隔離DBで未適用なし。共有AWS DBの状態を示すものではない |
| 静的ファイル | 各イメージで228件収集・620件後処理成功。ギャラリーの静的ファイルを含む。実S3/CDNは未検証 |
| readiness / deploy check | 各イメージでHTTP 200、database/cacheともok。migrate --check / check --deployが終了0 |
| 実イメージ内PG回帰 | 認証、Google連携、Calendar/Sheets配送、画像共有、JWT等146件が初期/修正後それぞれ成功（43.469秒 / 51.939秒）。SQLiteで省略されたOAuth競合2件も実行、省略0 |
| ソース照合 | 初期イメージのアプリ関連581ファイルはGit b3313a91と一致（3件はCRLF正規化後）。修正はDockerfileと構成テストのみで、アプリ本体は変更していない |

検証に用いた4コンテナ（初期/修正後Web、PG、Redis）は専用ラベル・イメージ・ポート公開なしを確認して停止・削除。専用internal networkも削除し、不在を再確認した。DB/Redisのtmpfs試験データは破棄、イメージとGit管理外の監査キャッシュは保持。実ユーザーデータを使っていない。

## 監査と残条件

初期イメージと修正後イメージのDocker Scout 1.24.0監査は、それぞれ専用キャッシュを作成したがindexingのcache-in-use timeoutで終了1。その後、[Docker公式の設定](https://docs.docker.com/scout/how-tos/configure-cli/)に従い、修正後の同一イメージを `DOCKER_SCOUT_NO_CACHE=true` で再確認し、268パッケージのindexingとSARIF生成が完了した。

- 指摘は16パッケージ・39件（HIGH 3 / MEDIUM 2 / LOW 34）、全件Debianパッケージ。CRITICAL/Python指摘は0だが、終了1でセキュリティゲートは未合格。
- 稼働版の71件から減少し、PCRE2とOpenSSLの対象指摘は検出されなくなった。両者の修正版パッケージも実物で照合済み。
- 残るHIGHはgcc-14由来の `CVE-2026-102010` / `CVE-2026-95619`、zlibの `CVE-2026-85091`。今回のスキャンでは修正版なし。Debianの[優先度付きキュー](https://security-tracker.debian.org/tracker/CVE-2026-102010)、[aligned new](https://security-tracker.debian.org/tracker/CVE-2026-95619)、[zlib](https://security-tracker.debian.org/tracker/CVE-2026-85091)の記録と対象経路の照合を継続し、勝手な除外やリスク受容は行わない。
- レポート: `C:/tmp/runtime-os-pinned-nocache-20261002.sarif.json`、SHA-256 `22c541de88658da9d64aa5b0166154fc9dfcf974feb0977af7dd6a7b6910dcf2`。
- 一時アーカイブのfile-in-use削除警告は残るが、指摘一覧の生成は完了。専用キャッシュは強制削除せず保持した。

Python依存の監査成功は[依存更新記録](DEPENDENCY_SECURITY_2026-10-02.md)を参照する。残るOS指摘の解消/判定、CI全体、実AWS/外部連携・性能・復旧は別の必須条件であり、正式公開No-Goを維持する。特にzlibやgcc-14由来の既知指摘を今回のPCRE2更新で解消したとは扱わない。

この変更はDBスキーマ・実データ・権限・継続費用を変更しない。コードを戻す場合は当該構築修正だけをrevertできるが、古いベース/PCRE2を再導入するため、安全性の回復策とはみなさない。

## 後続: ローカルPythonキャッシュの配布物混入を防止

構築修正は `2b4d0c4d` としてpush済み。そのコミット後ビルド `tableno:runtime-security-committed-20261002`（ID `sha256:22b2197d76f59c6a6a1a650b03cc6677bc5716f845a341dd9247ea66f2fd67fe`）を調べると、ローカルのPythonキャッシュ279ファイルが `/app` にコピーされていた。`PYTHONDONTWRITEBYTECODE=1` は実行時の生成抑止であり、ビルド時の既存ファイル混入は防がない。

- `.dockerignore` の `__pycache__` / `*.py[cod]` / `.pytest_cache/` を再帰的な `**/` パターンに変更。[Docker公式のパターン規則](https://docs.docker.com/build/concepts/context/#syntax)に従い、ルート直下と入れ子の両方を対象にする。文書の除外範囲や環境ファイルのルールは今回変更していない。
- 既存CIの `scripts/test/check_docker_build_context.py` に、ルート・1階層・深い階層のキャッシュ11例と、保持すべきPython/画面/静的ファイル等7例を追加。Terraformの既存検査も維持。実Dockerで修正前は8パス混入により失敗、修正後は除外20例・保持10例すべて成功した。ダミーファイルだけを使い、実データはコピーしない。
- 通常ビルド `tableno:runtime-context-clean-20261002`、ID `sha256:2fa85ae2015ffd3e3f4d31713dd3883132817f98c49a3abddd36f3813e0a8561` でも `/app` のキャッシュ0件を確認。上記コミット後イメージとの全ファイルSHA-256比較は、279キャッシュの除外と検査スクリプトの変更だけ。アプリ本体に差分なし、依存導入・不要パッケージ削除までの先頭10レイヤーも一致した。このIDは本追記前の検証用ビルド。
- 外部通信不可・使い捨てコンテナでDjango `check` と `collectstatic` が終了0。関連34テスト（Docker構成・リポジトリ整合性・文字品質）成功、既存Django非推奨警告4件。Black/isort/Flake8成功、利用者向けUI文言の変更なし。
- 検査スクリプトの成功経路の計測は34実行行中32行到達。今回変更した失敗メッセージの経路は修正前の失敗実行で確認済み。未到達の既存作業ディレクトリ保護例外まで100%とは扱わない。
- 追加のスクリプト単体Banditは既存コードにLOW 4件（subprocess関連3件、assert 1件）を報告、MEDIUM/HIGHは0。固定コマンドの引数配列・自前の一時ディレクトリ・合成fixtureのみで、shellや利用者入力は使わない。抑制設定は追加していない。

この修正によってOS指摘が解消したとはみなさず、上記39件の監査結果も新しいイメージの再スキャンとして転用しない。main/AWSへの追加反映、共有DB・権限・費用の変更なし。ローカルのキャッシュ自体は削除せず、ビルドへの送信だけを除外する。復旧はこの除外ルールとテストのコミットをrevert可能だが、キャッシュ混入が再発するため通常は前進修正を選ぶ。
