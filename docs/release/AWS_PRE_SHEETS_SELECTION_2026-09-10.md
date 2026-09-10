# Sheets対象指定修正の開発AWS反映

2026-09-10、承認済みの開発環境へのアプリ更新としてf16eb72bを反映した。Web定義45を複製し、コンテナイメージだけを変更した定義46への切り替えが完了した。

## 配布物と検証

- コード: `f16eb72b9c707fc1d8a76056f2b117b917199db2`
- タグ: `aws-pre-f16eb72b`
- digest: `sha256:eb03de941eccbf6432e331614d6aa4021cbb44120e09bf627a35a42c22f99aab`
- [push CI](https://github.com/sheepdog0820/iaia/actions/runs/34439632604)、[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34439634721)とも6ジョブすべて成功。Terraformの検査を追加した後の単体/統合テスト失敗は修正され、再検査を通過した。
- [通常イメージの隔離HTTP試験](GOOGLE_SHEETS_SELECTION_2026-09-10.md)15ケース成功。Google実送信は0件。

14:23 JSTの確認で、Web定義46が希望1・稼働1、rollout COMPLETED。タスク `755fa2f6bc3d4bd3be9275583a017cfc` はRUNNING/HEALTHYで、上記digestと一致した。readinessはdatabase/cacheともok。起動ログ22件にERROR/Tracebackなし、待受開始を確認した。

Chromeで更新後も指定アカウントのログインが維持され、ホームの年間26h・セッション43件、グループ表示が完了。連携設定はGoogle認可済み、Calendar/Sheetsの切替はともにOFFのまま。実環境でのGoogle出力・同期は実施していない。

## 変更範囲・復旧・残条件

DB移行、実データの試験書き込み、IAM/Secrets変更、Redis/worker常設化、Terraform適用は実施していない。背景透過定義3、タスク資源、環境変数、ロール、ネットワーク等は維持し、イメージ以外の定義差分がないことを照合した。静的ファイルの変更がないためcollectstatic・CloudFront無効化は不要だった。

復旧先はWeb定義45、digest `sha256:64a901c0d3b8e4ac84f05ec8c706f735e2a257fa18564b5cab7a01e3e79282ee`。必要時はサービスのタスク定義を45へ戻して正常性を確認する。ただしSheets空指定の不備も戻るため、外部出力を有効にする前に再修正が必要。

常設処理基盤、Googleへの限定データ実同期、トークン更新・取消・再試行、Stripe、事業者情報、全体の性能・復旧等の公開条件は残る。mainマージと本番公開は行っていない。OS監査の未解決事項も残り、CI成功だけで正式公開可能とは判定しない。

反映証跡はGit管理外の `tmp/aws-pre-f16eb72b-deploy/`。本資料を含む後続文書コミットのCIと、上記アプリコードのCI結果は区別する。
