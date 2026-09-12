# Google Sheets異常応答時のジョブ終了

## 問題と修正

Google Sheets出力のPUTがHTTP成功でも、本文がJSONとして解釈できない、またはオブジェクトではない場合、従来は例外が処理されずAsyncJobがRUNNINGのまま残った。null・配列・文字列・数値・JSON解析のValueErrorの5ケースで再現した。

応答解析の失敗とオブジェクト以外の結果を検出し、ジョブをFAILEDへ更新、終了日時と固定の日本語エラーを保存する。応答本文や解析例外の内容を利用者向けエラーに含めない。表示は「Google Sheetsの応答形式を確認できません。出力先を確認して再試行してください。」とする。

HTTPエラーの既存再試行、送信前の認可確認、RAW書き込み、正常応答の処理は維持する。HTTP成功後に本文だけが壊れる場合、Google側で書き込みが完了した可能性があるため、出力先を確認してから既存の再試行操作を利用する。実Googleの応答をこの試験で確認したとは扱わない。

## 検証

隔離SQLiteで以下33テストが成功（22.405秒）。新規テストでは上記5種類ごとにFAILED、終了日時、日本語エラーの一致、PUTが1回だけであることを確認した。既存テストでは正常出力、連携無効化・スコープ取消・ユーザー無効化による送信拒否、認可更新失敗とジョブ再試行を確認した。

```text
python manage.py test schedules.test_google_sheets_delivery tests.integration.test_google_job_authorization schedules.test_external_integrations schedules.test_async_jobs --noinput -v 0
```

Black・isort・flake8成功。差分と日本語エラー文を確認し、応答本文の漏出・追加送信・認可迂回は導入していない。変更対象はschedules/tasks.pyと専用テスト、本文書。DBスキーマ・実データ・権限・費用の変更なし。

CI、実Google出力、mainマージ、AWS反映は未完了。必要ならこの修正のコミットを作業ブランチでrevertし、関連テストを再実行する。正式公開全体の完了を意味しない。
