# アカウント削除E2Eのページ起動・操作予算分離（2026-10-06）

## 対象と原因の確認範囲

[先行CI37400351318](https://github.com/sheepdog0820/iaia/actions/runs/37400351318)のWebKit account-deletion失敗を、ログだけでなく[保持artifact11384699887](https://github.com/sheepdog0820/iaia/actions/runs/37400351318/artifacts/11384699887)のtraceで調べた。archiveは10,219,265 bytes、SHA-256 `2333eaf41e2c8f02561bb9ca1700711d68e7171666905a234fde8b65f87fc6dd` で公開artifact metadataと一致。選定したtrace・error-context・screenshotのみGit外へ取得し、未選定データは実行しない。

test.traceの `pw:api@37`（Create page）は496,012.388→516,597.237、**20,584.849 ms**。Before Hooks開始495,123.043、After Hooks開始525,980.741。最初の確認モーダルは表示・キャンセル・DOM撤去まで成功し、その後の操作中に全体30秒timeoutの後片付けが開始。最終の確認click（pw:api@65）はcontext close後にTarget page/context/browser closedで失敗している。表示・キャンセル同期の不具合やモーダルの永久待機を証明するtraceではない。

[Playwright公式timeout仕様](https://playwright.dev/docs/test-timeouts)はfixture setupが既定のtest timeoutに含まれることと、fixture専用の有限timeoutを設定できることを説明する。実際に使用するPlaywright1.63.0のbuiltin page fixtureとtimeout処理も確認した。今回の証拠はページ作成による操作予算消費を示すが、WebKit起動が遅くなったOS/renderer/CI負荷の根本原因までは確定しない。

## 修正と維持する条件

- `tests/e2e/fixtures/page-budget.ts` に専用factoryを追加。通常はpage作成へ独立した30,000 msの上限を与え、Playwrightの隔離contextで `context.newPage()` を呼ぶ。contextのtrace/video/後片付けは既存frameworkが担当する。
- account-deletion.spec.tsだけが専用fixtureを使う。操作本体・beforeEachの既定30秒、assertionの5秒、workers1・retries/CI failOnFlakyTests・trace保持は変更しない。context作成全体や他flowの時間枠を無条件に広げない。
- factoryの小さい上限指定は回帰probeの有限timeoutを高速に検証するために使用する。実削除flowは既定30秒を使用する。
- アプリJS/template/view/API・削除権限・パスワード/確認入力・Stripe非終端契約の防止処理は変更しない。ページ起動時間はtest wall timeに追加され得るが、実アプリ性能基準p95<3秒の変更や達成証明にはしない。

## TDDと時間枠の正負確認

先に実Playwright子runnerを使う回帰3ケースを作成した。最初のfactoryはbaseをそのまま返す未実装状態。2 failure/1 pass：起動時間による操作枠の消費とpage専用上限の不在を再現した。専用fixtureを実装後は3件成功（5.7秒）。

| 子runnerの条件（操作上限500 ms、retries0） | 期待と確認 |
| --- | --- |
| page生成350 ms＋操作350 ms、page上限1,000 ms | 操作の500 msを維持してpassed/終了0 |
| page生成0 ms＋操作900 ms、page上限1,000 ms | Test timeout of 500ms exceeded、timedOut/終了1 |
| page生成900 ms＋操作0 ms、page上限250 ms | Fixture page timeout of 250ms exceeded during setup、timedOut/終了1 |

失敗すべき子runnerの終了1を親probeが期待通り確認した場合に親testは成功する。これを子runner全成功と表現しない。mockするのはcontext/newPageのみで、実runnerの時間計測・fixture・test予算判定を使う。子probeはserver/browser/DB/Stripe/networkへ接続しない。config/specはmkdtempの専用directoryだけに生成し、絶対parentとprefixを照合して同directoryを後片付けする。

## 実ブラウザー・安全なローカル検証

ローカルサーバースキルで現在のworktreeを起動した。外部settings shimはDBを `D:/tmp/codex-account-deletion-20261006/isolated.sqlite3`、mediaを同専用directoryへ限定し、DEBUG/DBの絶対targetを確認してから使い捨てDBのみmigration。ENV_FILE空・Sentry/AWS secret入力なし・local設定でhealth200。元checkoutの実DBや共有DBへmigration/fixtureを適用していない。

実Chromium/Firefox/WebKitでaccount-deletion、arkham-confirm、page-budgetの計72件成功（193.171秒）、retries0・省略0・unexpected0・flaky0。projectの操作timeoutはすべて30,000 ms、workers1を確認した。通常削除/再ログイン拒否、誤password拒否、キャンセル時POST0、非終端Stripe契約past_due/revoked/activeでアカウント保持を含む。Stripe fixtureは新規隔離ユーザーのDB行だけを操作し、外部Stripe契約や実課金を作らない。Bootstrap有無の確認/取消/Escape/背景クリック/ドラッグ/外部close/繰り返し・開くアニメーション中の選択も回帰対象。全体suite・実AWS/SMTP/Sentry/外部連携の合格には拡張しない。

Node22.17の通常 `node --check` は.ts extensionを拒否した（source syntax判定ではない）。同runtimeの `--experimental-strip-types --check` と実Playwright loaderで変更3 TSの構文検証に成功。アプリ/UI表示文言変更なし。新しいprobeの説明は日本語で、英語はframeworkエラー照合・内部synthetic test titleのみ。

Node V8出力22件から新fixtureのfactory/page callback 2関数を照合し、区切り4区間の実行を確認（観測区間100%、未実行区間0）。failure側のawait後の狭いrangeのcount0は、成功側でその子rangeが省略された親rangeのcountを継承して照合する。初回の集計はPowerShell collection Countとcounterを混同し、その後の単純なrange別maxも親rangeの継承を扱わなかったため、いずれも最終coverage証拠にしない。最終は各process/functionで最も狭い包含rangeのcountを取り、process間で実行を照合した。これはtranspile後の上記2関数のV8観測範囲で、全アプリ/source-map statement/全test coverageの100%とは扱わない。

隔離User/Subscriptionは最終0件。PID45012・runserver command・skill PID fileを照合して今回起動分だけを停止し、port8000のlistenerなしを確認した。skillのStatus終了1はnot-runningという期待状態で、起動/検証失敗ではない。使い捨てDBと証跡は保持し、実データや元checkoutを削除しない。

## 影響・承認・残課題

今回変更はE2E3ファイルと証跡/受け入れ条件の2文書のみ。main/AWS・アプリimage/依存lock・共有DB/実データ・Secrets/IAM・課金/容量/継続費用・外部通知は変更しない。元checkoutの無関係13 itemsを保持する。復旧はこのtest/文書commitのrevert。先行favicon反映の承認に、今回変更を追加しない。

OS再scan・HIGH指摘の抑制/受容はしていない。HIGH3/native閉包・実課金/外部連携/運用・AWS性能/復旧/事業者体制の不足があり、正式公開No-Goを維持する。先行CIのflaky判定・後続の成功も消さず、今回の全CI/他flow/通常配布物は未確認として区別する。

文書関連39テスト成功（0.035秒）、相対参照208件/欠落0、証跡5ハッシュ一致。変更5ファイルの差分・UTF-8/LF/BOMなし検査に成功。全ステージ差分を自己レビューし、予算分離がapp性能条件や失敗受容になっていないこと、専用probeの失敗判定と後片付けの範囲を確認し、修正を要する指摘なし。アプリ/UI文字列の変更なし、新規の日本語test説明・技術用語/内部titleの例外を手動確認済み。TS以外のsource変更がないためPython formatter/全体Django testは対象外とする。

## 保持証跡

`D:/tmp/codex-account-deletion-20261006`（Git外）に元artifact、選定trace、外部local設定、ブラウザー結果とNode V8 coverageを保持する。元traceには隔離CIユーザーの合成入力が含まれ、public repoへ転載しない。

| ファイル | SHA-256 |
| --- | --- |
| playwright-37400351318.zip | 2333eaf41e2c8f02561bb9ca1700711d68e7171666905a234fde8b65f87fc6dd |
| test.trace | 2854f6bf133e2f27a8b855844d5a7594e2f3ac3c39322afd9ee900b3edaf190c |
| 1-trace.trace | e3daf93a5342aa23fee5454395e3958e0dd201da2ed1562819c2ab69f531e206 |
| browser-results.json | 48866864b24fa058fe2afbb6df753f32905e15ce85cbfee62f7b5381a0d04e8e |
| fixture-block-coverage-summary.json | 55c6a26ae90a7bb29b3c2e42aa555569af459c39164042d05e40a5513085e6cf |
