# Googleジョブ履歴の日本語状態表示・安全な再試行

## 対象と公開判断

親は `b71095f18437a5b88c01a7c8d1cdf023d96ca4e2`、作業ブランチは
`codex/google-job-presentation-20261009`。専用worktreeでのローカル実装・検証であり、
main・開発AWS・共有DB・Secrets・権限・課金・容量は変更していない。
faviconへの既存承認をこの変更へ拡張しない。正式公開 **No-Go** を維持する。

## 利用者への変更

- Google履歴を「処理待ち／対象待ち／処理中／完了／失敗／結果不明／確認が必要／期限切れ／再試行受付済み／状態不明」で表示する。
- Calendar同期・Sheets出力を日本語で識別し、対象待ちには一般的な待機案内だけを表示する。
- APIに `display_state`・`status_message`・`can_retry` を追加する。既存の `status`・結果・エラーは保持する。
- 202は受付の確認であり、worker開始・Google反映成功を意味しない。`queued=false` を結果不明と誤認する警告をなくし、進捗・結果を履歴で確認する案内にする。
- 履歴更新失敗は受付情報を保持して警告し、ネットワーク障害・503の操作結果不明警告は維持する。
- 再試行ボタンには明示的な真のヒントとFAILED状態を要求する。旧APIのヒント欠落・未解決・期限切れ・引継ぎ済み・壊れたpayloadでは表示しない。

## 安全条件と実装

`google_job_presentation.py` は一つのSQL snapshotで、独立実行記録、共有対象のholder、
先行FIFO、退役sequence、同じ所有者・種類のlegacy successorを調べる。
SQLite/PGのUUID表現差を正規化し、8ジョブの一覧をSELECT最大2回で検査した。
相手のjob ID・所有者・token・bindingはAPIへ追加しない。

表示ヒントは認可ではない。再試行APIは元ジョブの行ロックを保持し、未解決の独立実行記録が
あればFAILEDでも400とし、新ジョブ・配送を作らない。既存UNCERTAINの拒否文は維持する。
接続・所有者・認可の既存再検査を維持し、holder解除や限定回復を追加していない。
既知終了した実行だけ通常の再試行を許す。表示照会は新たな解除・分類を書き込まない
（既存の `mark_stalled_google_jobs` の呼出は変更していない）。

## TDD・回帰・画面の証拠

証拠は `D:/tmp/codex-google-job-presentation-20261009` に保存した。
backendは隔離memory SQLite／loopback PostgreSQL 18.3、外部Requests禁止、合成データのみ。
画面は専用SQLite・FileSystemStorage・locmemメール・外部Requests禁止の自分のserverを使用した。
通常の開発DBや既存の共有AWSではない。

| 検証 | 結果・範囲 |
| --- | --- |
| 初期RED | `red.log` 12試験、`red-guard-ui.log` 4試験で未実装と未解決FAILED再試行の不足を確認 |
| 追加RED | `red-ci.log` はPG CI選定不足、`red-malformed.log` は不正payload4ケースで失敗 |
| 初回回帰 | SQLite/PG各378試験・37失敗。UNCERTAIN文の互換、CSS/表示assertion、未終了fixtureを修正。失敗ログを保持 |
| 修正局所PG | `pg-corrections.log` 70試験成功・省略0 |
| 最終SQLite | `sqlite-regression-final.log` 379試験、失敗0、PG専用27省略 |
| 最終PG | `pg-regression-final.log` 379試験成功・省略0、終了0 |
| 差分coverage | `coverage-audit-final.json`：同一ソースhash、製品59文/24分岐先、新規テスト318文/42分岐先すべて実行、除外0。既存view全体は94%で、全体100%とはしない |
| ブラウザー | `browser-final-results.json`：Chromium/Firefox/WebKit、126成功、retry/skip/flaky0 |
| 実API→画面 | `browser-seam-results.json`：3ブラウザー×幅1280/390の6ケース成功。実APIの10ジョブ・9表示状態・再試行1ボタンが一致。API応答mock0、pageerror0 |
| JavaScript | inline全体の構文確認。実際の変更4関数を抽出してV8の30範囲すべて実行。テンプレート全体のカバレッジ100%とはしない |
| Python | 変更6ファイルのBlack/isort/Flake8、Bandit成功。差分check成功 |

実PGの4競合（Calendar/Sheets×未解決/終了済み）では、独立接続の実FOR UPDATE待機を観測し、
確定後に400または202となることを検査する。観測timeoutは成功扱いにしない。
初回supersession fixtureは直接claim/failだけでjournalがACTIVEのままだった。
通常execution_scope終了、または書き込み0の確定GET拒否後のfinishを明示し、FINISHEDを
assertしてから再試行する。未解決を許可するよう製品ガードを緩めていない。

初回ブラウザーのserver起動前・古いtemplate読込・ホーム画面のmock不足は失敗記録として区別し、
所有serverの確認/再起動と具体的なfixture追加で修正した。待機時間や合格条件を緩めていない。
実API画面のseed準備では、設定属性の欠落とtestserver Host拒否で停止した。
最初のHost拒否は合成利用者/予定だけを作成し、job作成0・外部送信0だった。
この部分状態を確認し、既存fixtureを再利用してloopback Hostで一度だけ10jobを作成した。
この準備失敗は製品の実Google連携障害とはしない。

## CI・配布・残る確認

親b710の[CI 37847710928](https://github.com/sheepdog0820/iaia/actions/runs/37847710928)は全6項目成功を
10月9日に読み取り確認した。これは今回の新製品変更のCIではない。
今回のcommit/push後のCI、通常新配布物の照合・検証は別に確認する。
新PG競合テストをProduction Database CIへ追加した。

今回の証拠はローカルソース・合成APIであり、新しい通常image・実Google・共有運用を証明しない。
全cleanup/退会/再連携・保持/秘密情報・全lock順・legacy停止/drain/移行・共有Sheets認可/濫用防止・
結果照合/限定回復は未完了。先行OSスキャン37指摘/HIGH1未合格、課金・外部連携・実AWS性能・
DB/S3復旧・運営条件も残る。T14のローカル表示確認とT01〜T15全体の完了を区別する。

## 復旧と片付け

共有環境は未変更なのでECS切り戻しは不要。作業ブランチの製品差分はGitで個別にrevertできるが、
未解決FAILEDを再試行可能へ戻す危険を確認せずに旧ガードへ戻さない。
専用server PID33920とPGの固定ID/label/image/tmpfs/volumeなしを確認した。
最終test DB消去・base DBのpublic表0を監査して、専用server・PG/tmpfs・正確な合成DB/mediaだけを
撤去した（`cleanup-final.json`）。合成データは試験用で、復旧が必要ならfixtureから再生成する。
ログ・coverage・script・画像の証拠と元checkoutの別作業13件は保持した。
