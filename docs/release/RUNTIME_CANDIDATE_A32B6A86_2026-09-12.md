# a32b6a86の配布物・公開前検証

## 対象と判定

対象コミットは `a32b6a866702a1ec0fb9ed1ec714d66574aa0692`。個人事業者・請求開示の表示、環境別設定例の統一、Calendar取消・再開・異常応答の処理を含む。正式公開はNo-Go。実Google・Stripe、問い合わせ受信/返信、復旧・監視等の受け入れ条件は未達。

## 通常配布物

git archiveから標準Dockerfileで `tableno-release:a32b6a86` を作成し、ビルド終了0。イメージIDは `sha256:c617a83ec0632db84248ea6ea33351bb92872b5c3c78e445b3d67c110ee542d2`、revisionラベルは対象コミットと一致。アプリ関連516ファイル（対象アプリ、templates、staticのPython/HTML/JavaScript/CSS）のSHA-256が固定ソースと一致した。

ソース差し替えなし、隔離テスト設定のみ読み込み、ネットワークなし・メモリSQLiteで280テスト成功（28.073秒、終了0）。次の対象を実行した。

```text
tests.unit.test_billing_legal_pages
tests.unit.test_public_legal_pages
tests.unit.test_production_settings
accounts.test_billing
schedules.test_google_calendar_delivery
tests.integration.test_google_job_authorization
schedules.test_external_integrations
schedules.test_async_jobs
```

外部APIは模擬応答であり、実課金・実Googleの成功を証明しない。設定例の文書検査は先行する61テスト・16サブテストの結果を参照。Git管理外の再現資料は `tmp/build-release-a32b6a86.py`、`tmp/release-a32b6a86-tests.log`、`tmp/release-a32b6a86-source-manifest.json`。

## 脆弱性スキャン

Docker Scout 1.24.0で上記イメージをスキャンし、SARIFを出力した。268パッケージを索引化し、15パッケージに41指摘（HIGH 1、MEDIUM 1、LOW 33、UNSPECIFIED 6）。件数・重大度の内訳は2a0ecbc6の同日結果と同じだが、これだけで全パッケージや到達条件の同一性は主張しない。

`--exit-code` を指定していないため、終了0は脆弱性なしを意味しない。既存HIGH等の適用条件と対処判断は未解決のまま。レポートはGit管理外の `tmp/runtime-a32b6a86-20260912.sarif.json`。スキャナーの一時アーカイブ削除でWindowsのファイル使用中の警告があったが、レポート出力は完了した。検証コンテナは `--rm` で終了している。

## 開発AWSの読み取り確認

2026-09-12 19:03 JST、アカウント083773015316・東京リージョンを照合した。ECSサービスはACTIVE、desired/running各1、pending 0、Web定義48のrollout COMPLETED。イメージdigestは `sha256:0e6255b3d0e8da2cea3c786371ae4ceafcad2ad23d321cf65c2bff0815990146` で、既存f97c7809の反映記録と一致。`/health/ready` はDB/cacheともokだった。

今回の候補はmain・AWSへ未反映。リソース・権限・Secrets・共有DB・実ユーザーデータを変更していない。既存稼働環境の限定した正常応答と、新候補の実サービス検証を区別する。

## CI

[push CI](https://github.com/sheepdog0820/iaia/actions/runs/34687367602)と[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34687370537)は、対象候補で双方とも全6ジョブsuccess。19:18 JSTまでに完了状態とログを照合した。

- 単体・統合: 1,817成功、30スキップ、カバレッジ87.11%。スキップ分を成功件数へ加えない。
- PostgreSQL: 293成功、48サブテスト成功。
- Playwright: 3ブラウザ計186成功。
- system、infrastructure、lint-security: success。

旧cf1448b9の設定例テスト失敗は、この候補の全体CIで解消を確認した。後続の検証記録コミットは文書のみで、CI結果の対象SHAは上記に固定する。CI成功はOS脆弱性や実サービス・運用条件の解決を代替しない。
