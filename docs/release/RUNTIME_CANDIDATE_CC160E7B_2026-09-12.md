# cc160e7bの配布物とCI検証

## 対象と結果

対象コミットは `cc160e7b84738d11ef3d6fa354364b397488a935`。Calendar取消・異常応答、個人事業者の請求開示表示、日程確定の性能改善、Sheets異常応答時の終了処理を含む。2026-09-12 20:40 JSTに[push CI](https://github.com/sheepdog0820/iaia/actions/runs/34690916435)と[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34690918069)が全6ジョブsuccessで終了したことをAPIで確認した。

- 単体・統合: pushログで1,820成功、30スキップ、159警告（867.36秒）。カバレッジ表示87%。スキップを合格数に含めない。
- PostgreSQL: pushログで293成功、48サブテスト成功、9警告（80.75秒）。
- ブラウザ: push・PRとも186成功（各11.9分）、flakyの報告なし。
- その他: system、infrastructure、lint-securityも両CIで成功。

先行6b70d517のFirefox登録遷移タイムアウトの原因が判明したという意味ではない。最新候補では両ブラウザCIが成功した事実と、先行候補での不安定な失敗記録を区別する。

## 通常配布物

git archiveから標準Dockerfileでビルドし終了0。イメージ `tableno-release:cc160e7b` のIDは `sha256:962c3c7a15456dbc8158b2e419de883c5e542c11d254a7d0aef59a8325c8c5eb`。accounts/schedules/scenarios/tableno/templates/static配下のPython・HTML・JS・CSS計503ファイルのSHA-256がアーカイブと一致した。

ソースの差し替えなし、外部ネットワークなし、隔離メモリSQLiteとテスト設定だけを使用し、以下47テストが成功（1.649秒）。試験コンテナは削除済み。

```text
python manage.py test schedules.test_google_sheets_delivery schedules.test_google_calendar_delivery schedules.test_external_integrations schedules.test_async_jobs tests.integration.test_google_job_authorization schedules.test_date_poll_response_queries --noinput -v 0
```

証跡はGit管理外の `tmp/release-cc160e7b-build.log`、`tmp/release-cc160e7b-tests.log`、`tmp/build-release-cc160e7b.py`、`tmp/verify-release-cc160e7b.py`。これは通常配布物の対象テストであり、実AWS・外部サービス・全UIの検証を代替しない。

## 未完了と反映範囲

mainマージ・AWS反映・販売開始は未実施。稼働版の最終確認は9月12日19:03 JSTのf97c7809/Web定義48。DBスキーマ・共有データ・Secrets・IAM・継続費用の変更なし。

Googleの実同期・出力と常設worker/Redis、保留中のStripe実テスト、開示窓口の受信・返信、全操作の性能、DB/S3を含む復旧・運用条件は残る。先行a32b6a86のOS指摘41件の解消も未完了で、本イメージのOSスキャン成功とは扱わない。正式公開は引き続きNo-Go。[全受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

この検証記録を追加する後続コミットは文書変更であり、上記CIの対象SHAとは区別する。復旧は対象変更のrevertと関連検証が必要で、旧コードの取消・異常応答・性能問題や請求開示設定の不整合を再導入しないよう確認する。
