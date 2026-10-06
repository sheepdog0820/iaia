# 退会E2Eの登録画面開始条件

## traceから確認した停止箇所

親は `25ef552e5026e92cc420f7793e126512e9cd79bb`、専用ブランチは `codex/signup-readiness-20261006`。[先行1690508e CI37422589768](https://github.com/sheepdog0820/iaia/actions/runs/37422589768)は5成功/Playwright失敗、終端は299 passed/1 flakyで終了1。Firefoxの非終端Stripe契約退会防止ケースがsignup page.gotoで30秒timeoutした。再試行成功をCI成功へ置き換えない。

[artifact11394315995](https://github.com/sheepdog0820/iaia/actions/runs/37422589768/artifacts/11394315995)を取得し、9,386,256 bytes/SHA256 `53b36deef6e0b0bf2f0c73308fa9a9416cc4574ea8077143a9b3cded96712b03` がCI終端の公開metadataと一致することを確認した。対象Firefoxのtrace/error-context/screenshotだけを展開し、archive内のソースを実行しない。テストユーザーの合成入力を含む元資料はGit外へ保持する。

ページ作成pw:api@28は236358.502→236552.347（193.845ms）。Navigate pw:api@29は236553.520に始まり、After Hooksは266532.349（29,978.829ms後）で開始する。最初の登録フォーム入力へは進まず、load待ちのgotoがtimeoutする。記録された17要求はすべてlocalhost/200、最大55.074ms、最後の完了はNavigate開始224.556ms後。失敗screenshot/error-contextに登録フォームが描画されている。[前回ページ作成予算](ACCOUNT_DELETE_PAGE_BUDGET_2026-10-06.md)の20秒起動遅延とは異なる。記録外要求の不存在やブラウザー/OSがload通知を止めた根本原因を断定しない。フォントbbox警告413件を観測したが、因果関係は未証明である。

## 対処範囲と維持する条件

- `tests/e2e/fixtures/signup-ready.ts` のopenSignupはsignupへDOMContentLoadedまで遷移し、非null応答/HTTP200、登録formの可視性、usernameの編集可能性、送信buttonの有効性を確認する。アプリのsignup初期化は既存templateのDOMContentLoaded listenerで行われる。画像まで含むload完了を登録開始の条件にはしない。
- 退会flowの初回登録2箇所だけで使用する。他画面のgoto/reload、page作成専用30秒、操作本体30秒、assertion既定5秒、workers1、retries/CI failOnFlakyTests/trace保持は変更しない。アプリ/template/権限/課金/サインアップ仕様の変更ではなく、ブラウザーのload問題全体を修復したという主張でもない。
- [Playwright goto仕様](https://playwright.dev/docs/api/class-page#page-goto)でDOMContentLoaded待ちを確認し、[自動待機・操作可能性](https://playwright.dev/docs/actionability)に沿って必要なフォーム状態を明示する。早期commitだけで初期化を省略したり、navigation例外を握りつぶしたり、タイムアウトを無限化しない。
- 新規5ケースは、画像応答を未完了にしたまま入力可能、外部初期化scriptを保留しDOMContentLoaded handler完了まで待機、HTTP500/フォーム欠落/入力・送信disabledの拒否を確認する。routeですべての要求を合成応答にし、実Google/Stripe/外部サービスへ接続しない。画像probeだけnavigationに有限3秒を指定するが、実退会flowの予算を広げない。

## TDD・ローカル検証

元のgotoだけを行う未実装helperで、実Firefoxの新規5件は4 failure/1 pass（12.2秒）、画像のload待ち750msと未検査のHTTP/form状態を再現した。helper実装後の初期3ブラウザー15件は成功（14.1秒）。その後、DOMContentLoaded handler完了・具体的な拒否理由の照合を強化した初回広域runは84成功/3失敗（245.557秒）。3失敗はHTTP500拒否のエラー文字列にANSI装飾が入って完全一致寄りの正規表現が合わなかったためで、HTTP拒否そのものは期待通り。製品の条件を緩めず、matcherResultのactual500/expected200/name/passを構造で照合するよう訂正した。初回ログ・report/traceは保持する。

最終広域は実Chromium/Firefox/WebKitの87件が成功（240.374秒）、retries0・skipped/unexpected/flaky0。account-deletion/arkham-confirm/page-budget/signup-readyの4 flowを対象に、通常退会・誤password拒否・キャンセルPOST0・退会後再ログイン拒否・Stripe past_due/revoked/activeで利用者保持を確認する。ページ起動/操作の正負予算例、初期化待ち/入力・送信可能性/HTTP拒否も含む。全projectの操作timeout30,000ms/workers1をreportで確認した。ローカルはCI環境フラグなしのためfailOnFlakyTests=falseだがretries0/flaky0であり、CIのfailOnFlakyTests条件はsourceで維持する。

Node最終V8出力22件からhelper openSignupの4観測sampleを照合し、1関数の区切り5区間がすべて実行済み（観測100%/欠落0）。各processの最も狭い包含rangeのcountを使い、成功側で省略される子rangeは親rangeから継承してprocess間で照合する。全アプリ/全TS/source-map statement coverageの100%ではない。集計確認コマンドの初回は過去のnative終了コードの取り違え、その次はパイプ構文誤りで停止した。集計script本体と試験結果の失敗とは区別し、専用PowerShell子processの終端0と最終JSONで確認した。

隔離User/Subscriptionは最終0件。PID43312のcommand/skill PID fileを再照合し、今回起動分だけをskillで停止、port8000 listener0を確認した。DB・元artifact・RED/初回広域失敗/最終成功のログとtrace・coverageは保持する。元checkoutの無関係13項目を保持し、実データや元checkoutを削除しない。

Node22.17/Playwright1.63.0、変更3 TSのexperimental-strip-types構文確認と差分検査に成功。signup focus/文書40テストは0.037秒で成功。新規利用者向けアプリ文言0件、日本語test名/合成表示を確認済み。TypeScript以外のアプリsource変更がないためPython formatter/全体Django testは対象外。

## 未確認・承認境界・復旧

2026-10-06 15:53 JST観測では先行28af6db8のCI37424071695は全6成功、25ef552eの37425603956は4成功/Unit・Playwright実行中。今回候補の全CI、元Firefox lifecycle停止の再現/根本原因、全flow・実AWS/Google/Stripe/SMTP/Sentry等は未確認。新しい開始条件だけで正式公開の性能・動作保証を証明しない。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実ユーザーデータ、schema/migration、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更しない。完了済みfavicon8567f49f承認や固定6b6c570c反映案を拡張しない。復旧はtest/文書commitの通常revertでschema逆移行不要。OS HIGH3/native閉包・実課金/連携/性能/運用/復旧/事業者対応等は未達のまま、[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goを維持する。

Git外証拠は `D:/tmp/codex-signup-timeout-20261006` の元ZIP、選定trace/network/error-context/screenshot、trace-summary、RED/GREEN/初回広域/最終広域ログ・report、隔離設定/DB、Node V8 coverage。使い捨てDBは同directoryのisolated.sqlite3に限定し、空ENV_FILE/DEBUG/絶対DB targetを確認してからmigrationした。ローカルサーバースキルで今回起動分PID43312を使用し、元checkoutの実DB・共有DBへmigration/fixtureを適用しない。

主要証拠SHA256は最終report `9648f0f0762b60ce6c7cddc577b8e24588a6add7f351da46687e0fc980dd11bf`、helper集計 `3e7f127f41f2fb7994dabea8ea8440ecb2a9cca4e50ac2ee2d66660a554df518`、trace-summary `f8cdacc233cff8ff196344dda3e6f88a9142468d7a8f370b67093dbf78feca15`、cleanup `8462600e83be9b0d8d1748d29aa2c342ce3967d2cad417327dcf29a4d869a614`。集計対象helper SHA256 `4d39a503835c3695765f4beb9542a04c20fee806e36fea7aad341931dbfd87a4` をsourceと照合する。
