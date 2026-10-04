# CCFOLIA・ICS修正の通常配布物検証（2026-10-04）

## 固定対象と結果

アプリ候補は `6b6c570c9df641244894930b497452491811aab2`。main `8567f49f` のアイコン・画像ギャラリー・承認済み依存更新を保持し、[CCFOLIAの版情報](CCFOLIA_EDITION_ROUNDTRIP_2026-10-04.md)、[ICSの文字・UTC時刻](ICAL_DOWNLOAD_INTEGRITY_2026-10-04.md)、[停止中アカウントの購読拒否](ICS_SUBSCRIPTION_AUTHORIZATION_2026-10-04.md)を含む。main・開発AWSへの反映はまだ実施していない。

クリーンな専用checkoutのHEADから通常のDockerfileで構築した。ローカルtagは `tableno:ics-candidate-6b6c570c`、固定image IDは `sha256:cdaa475f53dc0f24c6f612d756a61f6047aed4f138a99cc94166194458da3391`。Dockerfile・requirements・entrypointはmainと同じで、OCI revision labelや署名による来歴証明は追加していない。ECRへは未push。

- accounts/api/schedules/scenarios/support/tableno/static/templates内の対象拡張子とrequirements.lock/entrypointの追跡575ファイルをホストHEADとimageでSHA-256照合。欠落0・不一致0、Python cacheファイル0。image内Pythonパッケージ111件。全filesystemやビルド閉包の照合ではない。
- 候補の[CI run 37181732546](https://github.com/sheepdog0820/iaia/actions/runs/37181732546)はhead SHA一致、Unit / Integration・system・production-database・playwright・lint-security・infrastructureの全6項目success。2026-10-04 15:24 JSTまでに確認した。CIの依存監査成功と、後述するimage全OS監査の未合格は区別する。
- mainとの差分にaccounts/schedulesのマイグレーションファイル変更なし。共有DBの既存0065〜0067適用履歴・実スキーマを証明したものではない。

## 配布物内の関連テスト

imageのソースを重ね替えず、通信禁止・公開ポートなし・512 MiBの一時コンテナとSQLiteメモリDBで検証した。初回75件は71成功・4エラー、終了1。既存CCFOLIAテスト4件がimageにNodeのないため起動できなかった。アプリの期待値を変えたり、テストを省略して成功扱いにはしていない。

検証工具だけをread-onlyで追加し、同じimageで76件すべて成功（25.520秒、終了0、省略0）。Node v20.20.2のLinux archiveを[公式配布元](https://nodejs.org/dist/v20.20.2/)から取得し、公式SHASUMS256とSHA-256 `df770b2a6f130ed8627c9782c988fda9669fa23898329a61a871e32f965e007d` を照合した。抽出したnode binaryだけを `/test-tools/node` にmountした。配布imageへのNodeインストールやアプリソース変更はない。署名照合はしていない。

対象は `accounts.test_ccfolia_edition_roundtrip`、`accounts.test_character_ccfolia_export`、`accounts.test_character_6th_api`、`tests.integration.test_paid_feature_lifecycle`、`tests.integration.test_calendar_subscription_authorization`、`schedules.test_external_integrations.CalendarSubscriptionTestCase`、`tests.integration.test_calendar_feed_encoding`、`tests.unit.test_ical_text`、`tests.integration.test_ical_download_encoding`、`schedules.test_calendar_apis`。課金試験のStripeはmockで、実課金・メール配送の証拠ではない。

## 通常起動・実HTTP

同じimageの通常entrypointで、隔離PostgreSQL 18.3/Redisとaws-pre型設定を使った。PG imageは `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、Redisは `sha256:2e1c703aab5fd50a33e1bccdff0ae62260fb34f2f6cb9d696275c82180619a35`。PGはnetwork none・512 MiB・tmpfs、Web/Redisはそのnetwork namespaceを共有し、公開ポートなし。検証用DB・利用者・トークン・Stripe設定はすべて合成。SMTPは到達不能なloopback、購入開始と課金メール配送は無効。S3は使わない。

新規の空DBで通常entrypointの全移行とcollectstaticが成功し、Daphneが起動した。232ファイル収集・624 post-process、`check --deploy` は0問題、`migrate --check` は終了0。`billing_release_gate` は `ok checkout-disabled` であり、有料公開ゲート合格ではない。実AWSの起動時移行/静的収集フラグはfalseのまま。

localhostの実HTTP 19リクエストで、次を確認した。

- readiness 200・DB/cache正常、ログイン画面200・favicon link保持。
- 4つのfavicon/PNG公開URLが200で、image内元ファイルとbytes一致。
- manifest上のCCFOLIA helperが200・ソースとbytes一致。
- ICS購読: 有効時200・private/no-store、停止GET/HEADは404、再有効化後200、参加資格喪失後は非公開予定のUIDなし、再発行後は旧404/新200。
- 認証済みICSダウンロード200: UTF-8/CRLF・75 octet以下の行・単一VEVENT/2 ALARM・UTCのZ・locationのTEXTエスケープ。
- 通常の非staff/非superuser/非premium利用者のAPIで6版/7版をexport 200 → リクエスト側の版指定なしでimport 201。保存版・所有者・STR・7版の幸運55/70を保持。

HTTP harnessの初回は `/probe` からのmodule検索で `tableno` をimportできず、fixture作成前に終了した。再実行時に `PYTHONPATH=/app` を明示して成功し、assertionは変更していない。認証は隔離DBのDRF Tokenであり、実サインアップ/ログイン/OAuthの往復ではない。X-Forwarded-ProtoによるHTTPS相当ヘッダーを使用し、実TLS・ALB・S3・AWS・外部カレンダー・実CCFOLIAは検証していない。独立ICS parser/ブラウザー往復の先行結果は各修正文書を参照する。

検証後に、今回作成したWeb/Redis/PGコンテナだけを停止・削除した。PG tmpfsの合成データとRedis専用匿名volumeを破棄。実DB・他のコンテナは操作せず、imageと専用証跡は残した。

## 静的差分・脆弱性・現在のAWS

2026-10-04 15:24:37 JSTにS3の現在manifestとローカル収集manifestを読み取り比較した。双方232 mappingで、変更は `js/ccfolia_character_copy.js` のみ。現在 `js/ccfolia_character_copy.bb432b817259.js` → 候補 `js/ccfolia_character_copy.bf50da761ab5.js`。同じmappingの比較であり、232全配信内容のbytes照合ではない。

候補にDocker Scout 1.24.0の無抑制全パッケージ監査を実行した。268 package indexed、16 vulnerable packages、39 CVE（HIGH2/MEDIUM2/LOW35、Python0）、終了1。現在のfavicon image監査とCVE ID差分0。報告SARIFも同一SHA-256であり、修正による脆弱性解消はない。先行の組込みScout 1.5.0は259 indexedで、全監査の証拠には使わない。Scout cacheのWindows archive後片付けでfile-in-use警告が出たが、報告出力と終了1は確認済み。抑制・only-fixed・ベース除外・リスク受容はしていない。

15:24 JSTの読み取りではAWS定義54、image digest `sha256:adafc0705ded3dabf2a9d2223a5c460b48ff00b2c949f221a4edef3eedee695e`、CPU256/memory512・desired1、plain env52/Secrets参照19。直前15:07 JSTのrunning/pending=1/0・HEALTHY/readiness正常も確認した。RUN_MIGRATIONS/RUN_COLLECTSTATIC=false、STRIPE_CHECKOUT_ENABLED=False。課金メールのAWS実効設定/配送は未証明。

専用証跡は `C:/tmp/iaia-ics-candidate-6b6c570c`。`http_probe.py` SHA-256は `8918df9748b4ff38973012e4852d6a799a3b2e62184435c3a69dd4267b38090c`、全監査 `runtime-full.sarif.json` は `4924d757f193ce8edc27492ad5006bea0a41b61bb61c0d57c7221fb5b1f48f39`。合成env/工具/大量生成物はGitへ含めない。

mainマージ・ECR push・ECS更新・共有DB操作・S3書込み・CloudFront無効化は未実施。元checkoutのハンドアウト差分は保持した。[今回専用の反映承認案](AWS_APP_APPROVAL_6B6C570C_2026-10-04.md)を別途提示し、[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は維持する。
