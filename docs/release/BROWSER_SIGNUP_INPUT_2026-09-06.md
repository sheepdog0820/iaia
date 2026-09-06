# ブラウザ登録テストの入力確認

## 再発確認（44358a72）

[CI実行34018989095](https://github.com/sheepdog0820/iaia/actions/runs/34018989095)は、WebKitの同じゲスト登録フローが再試行時のみ成功し、179 passed / 1 flakyで失敗した。他の4ジョブは成功。入力方法の変更だけでは解決していない。

今回は入力前の `toBeFocused` に成功した後、確認用パスワードの `pressSequentially` が完了しても値は先頭8文字にとどまり、直後の `toHaveValue` が失敗した。未入力のまま送信を待つ問題は検出できるようになったが、文字入力が欠落する原因は未確定。登録APIの不具合やフォーカス喪失を断定する証拠ではない。タイムアウト延長や再試行で合格扱いにはしない。

artifact 9985015882を `tmp/signup-44358a72.zip` に保存し、SHA-256 `9fac82b762dcab3f91afc91eaffd32f8deb430388772b8e34a5682c28bed1d17` がジョブログのdigestと一致することを確認した。次の調査では入力イベントとページ・入力欄のフォーカス状態の変化を採取する必要がある。

以下は前回の調査・変更記録。

## 再発時の診断記録

通常登録テストの `signUp` に、入力・フォーカス・ページ可視性のイベント記録を追加した。パスワード一致のアサーションが失敗した場合だけ `signup-input-events` をJSON添付し、元のエラーを再送出する。入力方法、アサーション、再試行・失敗判定は維持する。

記録はイベント種別、時刻、要素ID、文字数、現在フォーカス要素、documentのフォーカスと可視性に限定し、最大300件とする。文字、キー、入力データそのものは新しい診断JSONに記録しない。既存Playwright traceの機密情報除去を実現する変更ではないため、引き続き合成ユーザーだけを使う。

一時コピーで期待値に1文字だけ追加して意図的に失敗させ、元のアサーション失敗が維持されることとJSON添付を確認した。98イベントを取得し、全項目が上記の許可項目だけでパスワード文字列を含まないことを検査した。この一時コピーはコミットしない。証拠は `tmp/signup-events-probe.log` と `tmp/signup-events-probe-output/results.json`。通常フローの検証結果は `tmp/signup-events.log` と `tmp/signup-keyboard-output/results.json` に保存する。

この変更は原因特定に必要な証拠を追加するものであり、WebKitの入力欠落を修正済みとは扱わない。アプリ、DB、権限、実環境の変更はない。

診断追加後の通常フローは3ブラウザ各8ケース、合計24ケースに合格（3.7分、再試行・スキップなし）。空のSQLiteと合成ユーザーを使う使い捨てコンテナーで実行し、終了後にコンテナーを削除した。バックエンドの変更はなく、アプリ全体のテストは再実行していない。

7ffd1f97の[CI実行34017232661](https://github.com/sheepdog0820/iaia/actions/runs/34017232661)は179 passed / 1 flakyでブラウザジョブが失敗した。再試行で成功しても合格にしない設定が働き、artifact 9984465650にトレースが保存された。

## 失敗箇所の証拠

WebKitの「anonymous guest joins and a normally registered user claims the participant」で、ゲストが通常アカウントを作成する2回目のsignupが進まなかった。signupのGETは200だが、送信ボタンのclick後にPOSTがなく、dashboardへの遷移待ちで30秒を超えた。context.closeのエラーはタイムアウト後の後片付けであり、最初の停止箇所として扱わない。

artifactのSHA-256をGitHubのdigestと照合した。ZIP内3-trace.traceの差分スナップショットをPlaywrightの記録形式に従い復元したところ、password1はfill完了直後から送信click後まで長さ0、password2は43だった。スクリーンキャプチャも確認した。入力していない状態で登録先への遷移だけを待っていたため、まずテストの入力手順と確認を是正する。なぜfillが空のまま完了したのかというブラウザ内部の原因は未確定であり、登録APIの不具合を実証した記録ではない。

ローカルの一時診断版ではfill直後の値とフォームのcheckValidityを確認し、WebKitの同フロー10回が成功した（2.7分、再試行なし）。毎回再現する問題ではない。この結果だけで元のCI失敗を解決済みとはしない。

## 変更

regular-user-session.spec.tsの共通signUpヘルパーで、両パスワード欄にfocusし、フォーカスを確認してpressSequentiallyでキーボード入力し、値が生成したパスワードと一致することを確認してから次へ進む。[Playwrightの入力操作](https://github.com/microsoft/playwright/blob/main/docs/src/input.md)に沿った通常のブラウザ操作を使う。DOMへの直接代入や登録APIでの置換はしない。

通常登録、独立したゲストcontext、招待失効、匿名操作の拒否、引き継ぎ前後の閲覧制御、再claim拒否、他ユーザーの権限確認は維持する。テストのタイムアウト・再試行回数・failOnFlakyTestsも変更しない。アプリのテンプレート、登録処理、DB、権限、実環境には変更しない。

## 証跡と検証範囲

CI artifactはtmp/axios-browser-ci-34017232661.zip、復元スクリプトはtmp/inspect-signup-trace.py。一時診断版の結果はtmp/signup-diagnostic.logとtmp/signup-diagnostic-output/results.json。修正後の通常登録関連の実行結果はtmp/signup-keyboard.logとtmp/signup-keyboard-output/results.jsonへ保存する。外部連携の実サービス検証を示す試験ではない。

修正後はChromium/Firefox/WebKit各8件、合計24件成功、再試行・skip・flakyなし、終了0。空の専用SQLiteと合成ユーザーを用い、既存テスト用イメージへ現行の共通テンプレート・Axios・対象テスト・Playwright設定を読み取り専用マウントして実行した。終了後に専用コンテナは削除済み。差分・UTF-8/LF・日本語文書をレビューし、アプリコードを変更しないためバックエンド全体の再実行は不要と判断した。push後の全体CIを別途確認し、不安定性の再発は引き続き不合格として扱う。
