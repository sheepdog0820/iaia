# Google認可更新・予定配送の配布物検証

## 対象とローカル検証

候補は `e85dd33026193affdbff7ea30bfcdad4970326bf`。認可更新の失敗を終了状態へ記録する修正と、Calendar作成応答の喪失後に同じ予定IDで復旧する修正を含む。

クリーンなgit archiveと通常Dockerfileから `aws-pre-e85dd330` を作成。ローカルimage IDは `sha256:65016666f72debcb5a9a9b03a6e50ccf1162de33002452ccf3a0e1e6fba0a190`。アプリソースを差し替えず、通常イメージの関連35テストとHTTPプローブ2件、計37テストが成功した。

HTTPプローブは実google-authのHTTP通信で認可更新拒否を再現し、Calendar/Sheets双方のジョブ終了・資格情報保持・外部書込みなしを確認した。別のプローブは模擬APIへの保存後に実ソケットを切断し、POST再試行・409・GET・PUTによって予定1件を維持し、変更したタイトルを反映できた。過去の自動採番IDを保存済みの場合もそのIDで更新する。

コンテナは外部ネットワークなし、DBはメモリ内の使い捨て環境。追加プローブだけを個別に読み込み、アプリソースは通常配布物のまま実行した。終了後にコンテナを削除。実Googleへの送信、実OAuth更新、複数worker競合の証明ではない。

## CIと反映

前候補5da23e35のCIは古い固定IDを返す模擬応答のため統合テスト1件が失敗した。e85dd330で修正し、[push CI](https://github.com/sheepdog0820/iaia/actions/runs/34445814677)と[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34445818404)は成功した。

その後READMEだけを更新した `f97c7809dd15acd2cabd3166ee84aa8eff2c6409` を今回の反映対象とした。[push CI](https://github.com/sheepdog0820/iaia/actions/runs/34455121479)・[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34455126552)はともに全6ジョブ成功。通常イメージ `aws-pre-f97c7809` をクリーンなarchiveから作成し、関連35テストも成功した。ローカルimage IDは `sha256:46c8f5f5bea89b119ee36951fd9b5fb815d8dc806579a75114f23dc8dd3de03b`。

ユーザーのmainマージ・開発AWS反映指示に従い、[PR #3](https://github.com/sheepdog0820/iaia/pull/3)をマージした。マージコミットは `74a4b50604a152a35e7fbb184203d2e02001aa1e`、そのツリーとf97c7809の差分は0。検証済みイメージをECRへpushし、Web定義47のイメージだけを置換した定義48へ反映した。

2026-09-10 17:47 JST、rollout COMPLETED・希望1/稼働1、タスク `997b85536851462c93aa19f86f3c64af` がRUNNING/HEALTHY。稼働digestは `sha256:0e6255b3d0e8da2cea3c786371ae4ceafcad2ad23d321cf65c2bff0815990146` で配布物と一致。readinessはdatabase/cacheともok。新タスクのログ29件にERROR/Tracebackなし。Chromeで既存ログインとホームの年間26h・43セッション表示を確認した。

DB移行、静的ファイル収集、IAM/Secrets変更、Google連携のON/OFF変更は行っていない。背景透過定義3を含め、イメージ以外のタスク設定は変更なし。復旧先は定義47、digest `sha256:ec7d36ca44210f7db5fd71d1267c8e892e6ce21668e4bff00b974e3f90c3c099`。サービスを47へ戻して正常性を確認する。復旧すると今回の認可更新失敗・作成再試行の修正も戻る。

Git管理外の反映証跡は `tmp/aws-pre-f97c7809-deploy/` のimage.json、state.json、service-current.json、tasks-current.json、verified.json。初期ローカル検証は `tmp/aws-pre-e85dd330-build.log`、`tmp/google_refresh_http_probe.py`、`tmp/google_calendar_http_probe.py` を参照。未承認のGoogle実サービス試験案は反映に含めていない。常設worker・実Google同期・Stripe・全体性能/復旧等の公開条件は残る。本番反映は行っておらず、正式公開は未完了。後続の文書コミット/main CIは上記の配布対象CIと区別する。
