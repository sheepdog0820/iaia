# タブレノのサイトアイコン反映記録

## 承認・対象

ユーザーのアイコン作成・反映依頼に対し、固定候補 `8567f49f8d411bad7f732afaeebad85357eeca09` のCI全6項目成功後にmainマージと `stg.tableno.jp` へ反映する計画を提示した。「main＋開発AWSへの反映を承認する」の明示回答を得た。対象は[サイトアイコン](../ui/TABLENO_SITE_ICON.md)のみで、前回のセキュリティ更新承認を流用していない。

| 項目 | 状態 |
| --- | --- |
| 基準main | `9ae40362783456956675e74f2ebf67666fe58028` |
| 対象アプリ | `8567f49f8d411bad7f732afaeebad85357eeca09`、専用ブランチへcommit/push済み |
| 候補CI | [run 37175249098](https://github.com/sheepdog0820/iaia/actions/runs/37175249098)、全6項目success。SHA/専用ブランチ一致を確認 |
| mainマージ | 13:09 JSTまでにfast-forwardで通常push済み。mainも同じ8567f49f、別内容のマージコミットやmainへの直接コミットは作成していない |
| main CI | [run 37176156903](https://github.com/sheepdog0820/iaia/actions/runs/37176156903)、13:26 JSTまでに全6項目success。SHA/main一致を確認 |
| 固定ローカルimage ID | `sha256:9c829979f8a69e075b61f7769c3b26d7a4fa003316c47d07e1982f7d7b94f4ad`、revision label=8567f49f |
| ECRタグ | `aws-pre-8567f49f`、push済み |
| ECR digest | `sha256:adafc0705ded3dabf2a9d2223a5c460b48ff00b2c949f221a4edef3eedee695e` |
| AWS反映 | 13:26 JSTに定義54を登録・Web更新。13:29 JSTにrollout COMPLETED、desired/running/pending=1/1/0、HEALTHY。稼働task `0abdbaf908314e939264db2bc6a99705` のdigestは配布対象と一致 |

## 事前検証

- `git archive` による固定checkoutから構築した。元のハンドアウト作業の未コミットファイルを含まない。
- 586個のアプリ・画面・静的資産等をarchiveと実イメージでSHA-256照合。欠落・不一致0、Pythonキャッシュ0。
- ローカルの隔離メモリSQLiteで関連15テスト成功、配信処理の行・分岐カバレッジ100%。配布イメージでも外部通信不可・read-only・一時/tmp・メモリDBで同15テスト成功。
- Black/isort/Flake8、staged差分・UTF-8/LF検査に合格。headリンク以外の画面本文・ナビゲーション・名称・ロゴは変更せず、日本語表示の変更なし。自己レビューで追加修正を要する問題は残っていない。
- ローカルChromeでICOの実取得HTTP 200、ログイン画面→利用規約→ログイン画面への遷移、console error/warn 0。ブラウザー操作用拡張機能がfaviconへ重ねるバッジはサイト本体の画像とは区別した。
- 確認用のローカルサーバーは終了後に停止した。既存の別サーバーや元worktreeには触れていない。
- Python依存ロック、Dockerfile、entrypoint、DBマイグレーションは直前の承認済み配布物と差分なし。前回監査のOS指摘39件（HIGH3/MEDIUM2/LOW34）は解消・受容済みと扱わず、新イメージの新規全OSスキャン成功を主張しない。

## 実行範囲・復旧

mainの通常マージ・pushとCI全6項目成功確認後、検証したECR digestでWeb imageのみ更新する。既存のCPU256/memory512、1タスク、IAM、Secrets、環境変数、ネットワークを維持する。migrate・DBデータ変更・課金有効化・OAuth操作・外部通知・常設容量増加は行わない。

既存ネットワークと新リビジョンを使ってcollectstaticを一時タスクで実行し、終了0、S3の新アイコン、CDN応答を確認する。`--clear` は使わず既存静的世代を残し、既存CloudFrontの`/static/*`を無効化する。アイコン自身はアプリoriginの固定公開ルートから配信するため、新しい静的manifestが到達する前でも取得できる。

反映前のS3 manifestはETag `dbd7fe4a93481a9d45141b6c7121b229`、19,891 bytes、version ID `mrsq4cIQnvHad7tPrS58Q18VJzBQWjKm`。内容が変わった場合は静的参照の前後比較にも使う。ローカルGitHub CLIは未認証で、未認証REST APIには直前タスクからのrate limitがあるため、接続済みブラウザーでrun/SHAを照合し、GitHubコネクターのジョブ取得でCIを確認した。別アカウントや資格情報の読み出しは行っていない。

復旧先は変更直前の定義53、digest `sha256:d9bd92ffec87642aeb1ae429623e9a3c762db9567b756f95151bef72c4ec056f`。起動・readiness失敗時はWebを戻してヘルスを再確認する。既存静的ファイルを削除しないため新アイコンを残しても旧版に影響せず、DBの逆移行は不要。

一時タスク重複・collectstaticタスク・ECR・通信・ログ・キャッシュ無効化の従量費用は発生し得るが、新しい常設リソースは作らない。本番反映・正式公開の承認ではない。

## 反映後の検証

- 定義53と54を全設定・タグで比較し、Web image以外の差分なし。環境変数・Secrets参照・IAM・CPU/memoryを維持した。
- 13:29 JSTにWeb安定化。readiness HTTP 200、database/cacheともにok。切替中にもreadiness成功を確認した。
- 稼働WebのCloudWatch起動後44ログイベントを確認し、Traceback・ERROR/CRITICAL・HTTP 5xx各0。自動migrate/collectstaticの起動記録なし。
- collectstatic task `35d0c9b85c744fcd8db98afb14862365` は配布digestと一致、STOPPED・exit code 0。`232 static files copied, 148 post-processed.`、Tracebackなし。migrateは実行していない。
- S3の新4資産それぞれについて原名・manifestのhash付き名の計8オブジェクトを取得し、配布元とSHA-256一致。旧manifestの既存対応は変更0。新manifest ETag `388634289af5fba73ae51f1910c952fe`、version ID `aWvgNwDceWv4joe9MTqBJGBblRKGz.aZ`。
- CloudFront `/static/*` invalidation `I2IHZF7QNFDG98Y4IWLQSL6RKV` は13:33 JSTにCompletedを確認。CDNの原名・hash付き名8 URLと、アプリoriginの公開3 URL・`/favicon.ico` はすべてHTTP 200、適切なICO/PNG MIME、配布元とSHA-256一致。
- ログイン画面と管理画面のHTMLはHTTP 200で、3種類すべてのsame-originアイコンリンクを確認。500画面は実障害を起こさず、事前のテンプレートテストで確認した。
- 開発AWSのChromeでログイン画面→利用規約→ログイン画面の実リンク遷移に成功、console error/warn 0。キャッシュ更新完了後の再読込でも表示正常・error/warn 0。ブラウザー操作用拡張機能のfaviconバッジはサイト本体と区別する。実iOS端末でのホーム画面追加と、実ブックマークの作成・再取得は未実施。
- 13:33 JSTの最終確認でも定義54・1/1/0・HEALTHY・指定digest一致、readiness HTTP 200でDB/Cache ok。ロールバックは不要だった。反映記録は専用の証拠ブランチへ保存し、配布アプリやmainには直接コミットしない。

この記録はアイコンの限定反映の証拠であり、正式公開の総合No-Goを解除しない。既存のOS指摘・課金実運用・外部連携・性能・復旧等の残課題は別管理のまま。
