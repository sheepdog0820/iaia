# 無料KPフローの登録開始条件とCI検証

## 対象と失敗の証拠

基準コミットは `77192584719631d7b7002f07d68ca57561bfc046`、専用ブランチは `codex/free-signup-readiness-20261007`。共有対象の排他実装がある別worktreeの未コミット6ファイルと、元checkoutのハンドアウト作業は含めない。

[基準CI37540663348](https://github.com/sheepdog0820/iaia/actions/runs/37540663348)は完了・failure。System、Lint/Security、Infrastructure、Unit/Integration、Production Databaseは成功、Playwrightは428 passed/1 flakyで終了1。Firefoxの無料KPフローが `/signup/` の `load` 待ちで30秒上限に達した。再試行成功を全CI合格とは扱わない。

artifact11449591599のZIPは9,534,738 bytes、SHA256 `4b1ead73c42a4409f5cd296f7dc0786e9acee7d3aedd1649d5bd67d34fcfb837` を照合した。失敗ケースのtrace、error-context、screenshotのみ固定名で展開し、アーカイブ内のソースを実行していない。画面とDOM記録には日本語の登録フォームが表示されている。

traceのnewPageは150.630ms、navigationは終了処理を含め30,102.421ms。記録されたHTTP17件はすべて200、最大53.084ms、最後の記録済み応答完了はgoto開始から195.916ms。consoleはFont Awesomeの字体bbox調整warning413件のみ。これだけでDOMContentLoadedの発火やフォーム初期化完了、未記録の通信、browser lifecycle遅延の原因を証明できない。元CIの根本原因は未確定のまま保持する。

## 修正範囲とRED

- 無料KPフローの登録開始に既存の `openSignup` を使用する。DOMContentLoaded、HTTP200、フォーム表示、ユーザー名入力可能、送信ボタン有効を確認する。helper本体やアプリの登録処理は変更しない。
- 通常ケースを残し、実Djangoの登録HTMLへ合成の読み込み待ち画像だけを追加するケースを同じ一連フローに追加する。画像解放前にdocument.readyStateがcompleteでないことと、各登録欄の入力を確認する。画像はfinallyで解放し、正常経路のroute終了を待ってから本来の登録POSTを行う。
- 同じ登録POST、dashboardへの復帰、無料シナリオ画面、CCFOLIAインポートの201、API再取得の名前一致、390×844の画面、6版/7版の最大5枚表示を維持する。無料権限や所有者確認をmockで置き換えない。
- helper導入前の画像待ちケースはFirefoxで30秒timeoutした。初回REDは終了時のunrouteAllによるclosed-page例外が元のgoto失敗を覆ったため記録を保存し、unrouteAllを正常経路へ移した。訂正REDは元の `page.goto(load)` のtimeoutとして失敗、retry0。終了処理の例外を握りつぶして成功扱いしない。
- Playwrightの30秒制限、CIのretries/failOnFlakyTests、workers1、アプリsource、依存、schemaは変更しない。テスト専用DOMの空altを除き新しい利用者向け表示文言はない。

## 検証

初回GREENはChromium/Firefox/WebKitの通常/画像待ち6件成功、39.9秒、retry0。最終広域は同3ブラウザーの93件成功、274.570秒、retry/skipped/unexpected/flaky0、failOnFlakyTests=true、workers1、各project timeout30,000ms。退会保護、確認ダイアログ、ページ予算、signup-ready、無料KPの5 flowを対象とし、初期化script待ち、HTTP500、フォーム欠落、入力/送信無効を成功扱いしないことも確認した。登録focus/公開文書の40件も成功。

測定前後と現ソースのSHA256 `858bd0193b355088ecddb985f4a1f6024c3ad8859a1e6946d1a45af58c58d8b9` は一致。Node V8の無料KP driver8関数は未実行区間0。シリアライズされるdocument.readyStateの1関数はNodeでは実行されず、画像待ちの3ブラウザーで実行しassertion成功を別に照合した。既存openSignupの5区間も未実行0。これらは変換後のV8区間とブラウザー実行の証拠であり、全TypeScriptのsource-map付き文/分岐coverage100%とは主張しない。新規アプリコードはない。初回coverage解析はPlaywright cacheのSHA-1コメント44 bytesを実行ソースへ誤算入して失敗したため記録を保持し、header除去後のモジュール長一致を必須として再解析した。

隔離設定はGit外、空ENV_FILE、APP_ENV=local/DEBUG=true、絶対パス `D:/tmp/codex-free-signup-readiness-20261007/isolated.sqlite3`。メールはlocmem、課金開始/課金メール無効、Celeryはmemory、cacheはlocmem。新DBのみmigrateし、local-serverスキルで専用checkoutから起動した。共有DB・実アカウント・実Stripe/Google/通知には触れていない。

終了後は絶対DBパスと全usernameの合成prefixを確認し、合成User12/Character12のみを削除、User/Subscription/Character残存0。起動したPID9156と子39484の実行コマンド・skill PID fileを照合し、skillで自分のサーバーのみ停止、両processとport8000 listener残存0。ログ・DB・証拠は保持し、テストから合成データを再生成できる。元checkout13項目と排他側6ファイルを再確認して保全した。

Node22.17.0/Playwright1.63.0を使用し、package-lock一致を確認した既存node_modulesへのローカルjunctionのみを用いた。変更TSと既存helperの構文、diff whitespace、staged4ファイルのUTF-8/LF検査に成功。新しい利用者向けアプリ文言はなく、既存の日本語入力/表示と空altを確認した。差分のsourceレビューで追加修正を要する問題は残っていない。文書更新後の登録focus/公開文書40件も0.036秒で成功。Python sourceの変更がないためPython formatter/アプリ全体テストの追加実行は対象外。Issueは権限不足で未作成のため既存の下書きと受入表に状態を更新し、認証や権限を変更しない。

## 残る条件

今回候補のCI全6成功、元Firefox lifecycle遅延の原因確定、Google共有対象の排他/結果不明/回復、通常配布物と実外部連携、OS HIGH3、運用・性能・復旧等は未完了。main/AWSへ反映しておらず、完了済みfavicon反映の承認を転用しない。正式公開No-Goを維持する。

証拠の保管先は `D:/tmp/codex-free-signup-readiness-20261007`。元CI artifact、初回/訂正RED、GREEN、広域結果、source照合、coverage、cleanupをGit外に保持する。修正はE2Eの開始条件と回帰ケースのみで、アプリ/DBの復旧操作は不要。戻す場合はこの専用変更のみをrevertし、他のGoogle実装やハンドアウト作業を破棄しない。
