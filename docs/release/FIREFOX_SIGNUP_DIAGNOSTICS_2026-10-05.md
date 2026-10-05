# Firefox初回登録ページ遷移の調査（2026-10-05）

## 結論と固定対象

最新アプリ候補は `6828f2095332c02c8fe0a965b5978ba736515f56`。同候補のCI全6ジョブは成功し、ローカルの既存退会フロー30件も成功した。ただし先行 `f355df1c` のFirefox初回遷移timeoutの原因は未確定で、再現・解消済みとは扱わない。アプリ、テスト、timeout、waitUntil、retry、failOnFlakyTests、ブラウザー対象は変更していない。

記録ブランチは `codex/firefox-signup-diagnostics-20261005`。GitHub mainは読み取り照合で `8567f49f8d411bad7f732afaeebad85357eeca09`。AWSは今回再照合・変更していない。固定6b6c570cの反映案や完了済みfavicon承認へ後続変更を追加しない。共有DB・実Stripe・Secrets/権限・実メール・課金・容量/継続費用も変更していない。正式公開 **No-Go** を維持する。

## CIの区別

| 対象 | 最終結果と検証範囲 |
| --- | --- |
| [f355df1c / run37209632857](https://github.com/sheepdog0820/iaia/actions/runs/37209632857) | 全体failure。Playwrightは290 passed / 1 flaky、終了1。その他5ジョブsuccess。Firefoxのaccount-deletion.spec.ts:5で最初の `/signup/` gotoが30秒上限に達した。retry成功を合格にはしない |
| [6828f209 / run37211219662](https://github.com/sheepdog0820/iaia/actions/runs/37211219662) | SHA一致・completed/success。production-database、playwright、system、Unit / Integration、infrastructure、lint-securityの6ジョブsuccess。Playwright **291 passed、16.6分**、flakyなし。pytest **2176 passed / 69 skipped / 159 warnings、604.71秒**、全体行カバレッジ88%。billing_release_gateはcheckout-disabledでok |

後続CIの成功は[コマンド例外・SDKログ修正](STRIPE_COMMAND_ERROR_REDACTION_2026-10-04.md)を含む候補の自動検証結果であり、先行timeoutの因果証明、未検証の通常配布物、AWS、実決済、外部連携、公開条件全体の成功ではない。失敗runの再実行はしていない。

## 失敗traceとHTTPの観察

接続済みGitHubからartifact `11306586956`（playwright-artifacts、9,303,300 bytes）を取得し、ダウンロードZIPのSHA-256をGitHubのartifact digestと照合した。最初のGitHub CLI経由取得は未認証で失敗したため、既存接続の読み取り取得を使用した。認証設定は変更していない。

- 失敗は登録POSTより前。CIログでは初回GETが2026-10-04 14:38:38.809 UTC、retryのGETは14:39:10.868 UTC。その後の登録POST・退会フローはretryで成功した。
- `1-trace.network` のHAR記録は **17件**、すべてHTTP200、hostはlocalhostのみ。document1、font7、image2、script3、stylesheet4。記録済みrequest timeの最大は58.708ms。ただしHARに存在しない未完了要求まで否定する証拠ではない。
- 失敗スクリーンショットには登録フォームが描画済み。gotoのbefore/logはあり、afterはない。traceだけでは失敗時のdocument.readyState、loadイベントの到達、未完了要求0を確認できない。
- console413件はFontAwesomeのglyph bbox警告で、約82msに集中していた。警告の存在を遷移停止の原因とは判断しない。
- 登録後の削除処理・パスワード拒否・課金契約ガードが原因という証拠はない。一方、描画済みという理由だけでアプリ側要因を除外もしない。

公式リポジトリの[Playwright issue42183](https://github.com/microsoft/playwright/issues/42183)は、旧SDK1.61.1/1.62.0のFirefoxで描画後もgotoが未完了になる報告。2026-08-13にclosed/completedだが、2026-10-05取得のコメントとtimelineにPlaywright自身の修正commitや適用版は確認できなかった。今回との症状の類似は調査候補に留める。今回のtraceは同報告のreadyState/load/未完了要求の全条件を証明せず、SDK1.63.0も異なるため、既知不具合と断定・独断の依存更新・待機緩和を行わない。

## 隔離ローカル試験

Windows / Node22.17.0 / Playwright1.63.0 / Firefox155.0。対象は通常Docker配布物ではなく、固定候補の作業checkoutとローカルPython環境。専用設定はENV_FILE空・APP_ENV localをassertし、専用SQLite、locmemメール/cache、専用MEDIA_ROOTを使用。Stripeキー空・購入開始/課金メール無効。実ユーザーDB・外部メール・実Stripeを使用しない。

ローカルサーバースキルで127.0.0.1:8002へ今回専用サーバーを起動した。既存8000サーバーは起動しておらず変更しない。空の合成DBだけへ移行を適用した。

| 試験 | 結果 |
| --- | --- |
| Firefox初回表示30回 | 各回新しいbrowser/context、goto load・30秒。全30回HTTP200、readyState complete、form visible/button enabled、pageerror0。最小433ms、最大1296ms、nearest-rank p95 612ms |
| ページ通信制限 | 初回表示probeはページ要求を127.0.0.1:8002のoriginだけへ許可し、blocked0。ブラウザー全体の背景通信を隔離したという意味ではない。1回はgoto成功直後favicon要求がpendingだった |
| 既存account-deletion 2フロー | Chromium/Firefox/WebKitそれぞれ5反復、計 **30 passed / skipped0 / unexpected0 / flaky0、401.846秒**。timeout30秒、retries0、workers1、failOnFlakyTests true。既存assertとload条件を維持 |

後者は合成ユーザー登録、取消、誤パスワード拒否、退会後ログイン拒否と、合成Stripe契約past_due/revoked/activeの退会拒否・ログイン保持を検証する。契約fixtureはローカル専用guardを通したDBレコードで、Stripe APIへの実接続ではない。フローはlocalhost:8002、初回表示probeは127.0.0.1:8002。CIのLinux環境を忠実に再現した試験でも、AWS100人/同時10人の性能ゲートでもない。

完了後、専用DB名とlocmemメール設定を再assertし、ユーザー残数0を確認。記録済み親PID37428・子PID30736のexe/親子関係/起動時刻/command/portを照合し、スキルのStopで停止した。8002のlistenerなしを確認。証跡・再作成可能な合成DBを保存し、共有環境や元checkoutの未コミット変更は触らない。

## 次の作業と復旧

新しいCIは成功したが、先行timeoutの原因は未確定として保持する。再発時には同じrunのtrace/HTTP/画面とnavigation/lifecycle/未完了要求を照合する。再試行成功だけでgateを通したり、timeout増加・待機条件の短縮・ブラウザー除外で隠したりしない。

最新コマンド修正を含む通常配布物の構築・同一性・隔離回帰は次の未完了項目。OS39指摘、管理運用方針、共有DB/worker/SMTP、実RAK/Endive/外部連携、AWS性能/整合復旧、事業者運用は引き続き未達。この記録だけをrevertしても稼働版には影響しない。

## 保存証跡

保存先 `C:/tmp/iaia-firefox-signup-20261005/`。大量trace・個別fixture・生成ログはGitへ含めない。

| 証跡 | SHA-256 |
| --- | --- |
| firefox-f355-playwright.zip | 3306aeb578d01fb8d2ad636901174c5ffe6fe53465e837288c8c1d6eb559ee3d |
| ci-f355/test-results/account-deletion-account-d-a4379-then-ends-the-login-session-firefox/trace.zip | c16699373c051e0b7bd0f4b6914b12bd31a6d6f3d7720b019aaa8a528c735595 |
| cold-navigation.jsonl | ec319b611bc14a2b5fd785f17b817ce057b11e5735643f660c55e1a97186610d |
| full-flows.json | cdffdce7092f978df2e1f206e96965166e0dfca38c3f1fa92e943c539badd118 |
| full-flows.log | d35de230ca5fb75ad275d66bea98aafe7e2f19985d826be75f60b21d42b3d7c2 |
| navigation-probe.cjs | 42260051d2c4e0099fbba3937cbdfe92f5c657afd8658eafb1544f68f3899db9 |
| flows.config.cjs | 1fa78f75a1c96bd3ee7966bcb8ec29764a33f266ba361bfa8923c5762143ee35 |
| signup_probe_settings.py | d43eadf106bd3bb080e9e882bb46cd644dd46077fbb68972f260ffdb6d865418 |
