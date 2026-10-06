# Google連携の投入結果不明時の画面案内

## 問題・変更範囲

[実Redis・2 worker配送検証](GOOGLE_REAL_BROKER_2026-10-06.md)で、APIのqueued=falseでも実受信workerが成功する例を確認した。連携設定のCalendar同期/再試行が「開始できませんでした、もう一度」と表示する点、Sheets出力が通信例外を処理せずボタンもロックしない点を修正する。親は `939118d7a3d66bfc6033f1f33f566109ef83dea3`、専用ブランチは `codex/google-dispatch-ui-20261006`。

- 3経路で共有するreport処理を追加する。queued=falseは開始状況が不明と案内し、ジョブIDを保持して履歴を更新する。もう一度投入する前に履歴で結果を確認するよう案内し、未配送/確定失敗を断言しない。
- queued=true（既存互換の未指定も含む）は従来の作成メッセージを維持する。一覧取得失敗は受付/不明メッセージとIDを残し、ページ再読み込みによる確認を案内する。一覧障害を新しい投入失敗に変換しない。
- 通信例外/5xxは処理が進んでいる可能性と履歴確認を案内する。401/403はログイン/操作権限の固定日本語、その他は既存detail（文字列）または固定日本語へ分岐する。5xx/認証エラーの内部detailを画面に表示せず、textContentを維持する。
- Sheetsにもtry/catch/finallyとボタンロックを追加し、3経路のdisabled再入を拒否する。処理後は従来どおりロックを解除する。外部書き込みのexactly-once・別jobの再投入防止・恒久的なロックを保証しない。
- 画面内の警告メッセージだけにBootstrap text-darkを追加する。Discord等で同じ欄に表示する警告にも適用するが、ページ全体のCSS/配色を変更しない。既存DOMContentLoadedスコープ内で共有し、onclick/global APIやナビゲーション構造は追加しない。

製品変更はtemplates/integrations/settings.htmlのみ。既存Python画面確認と統合E2Eの期待値を更新し、新規google-dispatch-outcome.spec.tsを追加する。API/workerの処理・レスポンス契約、DB/schema、依存を変更しない。

## TDD・検証途中の失敗

修正前のDjango画面確認は新日本語がないため1 failure（22件中）となった。初回ブラウザー3件はサーバー起動前の接続拒否で、UI REDには数えない。次の3件/36件は共通ヘッダー通知API fixture不足で終了1。fixture訂正後の36件は、noreloadサーバーに残った修正前テンプレートcacheに対して31失敗/5成功となり、旧案内・Sheets例外/再入の失敗を観測した。通常のDB回帰と別プロセスのHTTP表示を混同しない。初回から全成功とは扱わず、終端を確認してから自分のサーバーだけを照合・再起動した。

可読性の修正前も画面静的確認1 failureを確認した。対比変更前の3ブラウザー135件は成功したが、最終版の追加濃色assertion検証とは区別する。

補助コードの起動設定確認（存在しないUSE_S3_STORAGE属性）、AST parserのfilename不足、Windowsのconhost childの停止前照合、画面probeのCSRF複数要素/ホームAPI fixture不足/未認証APIの期待403と実際401の相違も途中失敗として記録した。製品設定・認証仕様・合格条件を変更せず、helperの前提を訂正した。失敗した画面probeの生きたプロセスを完全commandで特定し、そのbrowser treeだけを終了した記録を保存する。

## 検証範囲と結果

環境はWindows/Python 3.11.1・Node 22.17.0、空ENV_FILE/local設定・既存venv/Playwright・合成SECRET_KEY。専用 `D:/tmp/codex-google-dispatch-ui-20261006/isolated.sqlite3` とmediaのみを使用し、admin/investigator1/2を既存の開発コマンドで作成した。ローカルサーバースキルで空port8000を確認し、対象checkoutの通常manage.py開発サーバーで起動した。Docker通常配布物の追加検証ではない。実Google/AWS資格情報・外部通知を使わない。ブラウザーのGoogle/ジョブAPIは合成応答であり、実配送/実Googleの追加試験ではない。

- 対比修正前の関連回帰80件成功（29.433秒・終了0）。schedules.test_external_integrations、schedules.test_async_jobs、tests.unit.test_text_quality、tests.unit.test_release_documentationを対象にし、文書39件を含む。
- 実ソースからASTで抽出した新しい共通表示/エラー処理・showMessage・3クリック処理の6対象はV8 43区間すべて実行。既存displayFailureMessageも含めると7対象48区間・未実行0。queued真/偽/未指定、refresh成功/失敗、error/response/dataの欠損、401/403/400/5xx、文字列/非文字列detail、再入/no target、catch/finallyを確認した。inline全体を構文検査し、source fragmentは変更せずVMのDOM/API fixtureで実行した。テンプレート全体の100%や実ブラウザーの分岐coverageとは区別する。
- Chromiumの別probeでデスクトップ1280×900・モバイル390×844を画像確認した。警告文字RGB33/37/41と合成背景247.7/240.8/227.9の対比13.706:1、role=alert、Enterによる送信、履歴更新、document横はみ出し0。画像確認前後の2版を保存する。表の内部横スクロールは既存仕様として維持する。
- ホーム/キャラクター一覧/カレンダー/セッション/シナリオ/グループの実HTTP200、戻る/再読み込み後の履歴表示、未認証画面302/API401、存在しない画面404、pageerror0を確認した。Google APIはfixtureのままで、実認可検証にはしない。

最終の対比assertionを含む3ブラウザー135件が成功（303.152秒・retry/skip/flaky0・終了0）。新規3経路×12ケース×3ブラウザー108件に、既存設定保存21件・統合操作/実ゲスト引き継ぎ6件を加える。最終の関連回帰80件も成功（29.757秒・終了0）。Black/isort/flake8/Banditの変更Python確認・差分チェックは合格。通常配布物や実Googleの成功には拡張しない。

18:08:55 JSTに専用fixtureをread-only SQLで監査し、合成3ユーザー・Guest E2E group/session各6・Google job0を確認した。起動PID/child/port owner/commandを照合し、サーバーを停止してport8000の閉鎖を確認後、解決済みの正確なisolated.sqlite3だけを削除した。再生成可能な合成データのみで、実データを削除していない。ログ/helper/初回証拠/画像を保持する。

## 残条件・承認境界・証拠

18:04 JST確認で親939118d7の[CI 37437743341](https://github.com/sheepdog0820/iaia/actions/runs/37437743341)は全6ジョブsuccess。今回候補のCI/通常配布物・実Googleは未確認。OS再監査/依存更新は今回行わず、直前のHIGH3・39指摘/終了2は未合格のまま。outbox/外側transactionの未commit、broker TCP応答消失、worker crash/lease/常設Redis/別job重複・failed retry競合、永続接続先ID/再認可方針などの不足をUI修正で解消したとはしない。

main/AWS、共有DB/schema/実データ、Secrets/IAM、課金有効化/容量/継続費用、正式通知を変更しない。完了済みアイコン8567f49f承認・固定6b6c570c反映案に追加しない。実課金/外部連携/運用/性能/復旧/事業者対応の[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は未達で、No-Goを維持する。関連GitHub open Issueは無関係なUI #1のみ、先行の関連Issue作成403を別認証/権限変更で回避しない。

証拠は `D:/tmp/codex-google-dispatch-ui-20261006/` の初回/再試験ログ、Playwright結果・trace、V8/helper、専用設定/起動停止記録、遷移/対比JSON・画像へ保存する。生成物をGitへ混入しない。文書・画面の復旧は通常revertで、外部書き込みやschemaの巻き戻しは不要。

文書追加後の回帰39件成功、下表6 SHA-256/相対リンク2件/試験済みsource4件の一致、変更6ファイルのUTF-8/LF・staged差分確認に合格した。日本語UI/対比・実測と未確認範囲を自己レビューし、追加の指摘なし。元worktreeの無関係な未コミット13項目を保持する。

| ファイル | SHA-256 |
| --- | --- |
| browser-results.json | b91f169f63397c920d2800a3f4eb179d28204dbccca75afd3ce910eacef8ae66 |
| regression-final.log | 3547cf0f95898647e5a6a5bafba8008052b6440d4d3c4ec5df4d04ae53a0bbe2 |
| javascript-coverage.json | 3cfd210adaca81bf40f08c3cc6763612174a68b4af8a60c64a8a3b3c47bcaf95 |
| visual-results.json | 6e8c3b79f7d359e078e7952e274915b6033459f0db5f8ffd2e13d772dfa64704 |
| cleanup.json | f7511fc8f830e32a95db79b6992e1abc3ed6306f59687769e05b6a33399a0045 |
| tested-source-sha256.json | 3aaf69258b078653ea7df2b964fc87a713d041337d3ddea04f83a62104cafceb |
