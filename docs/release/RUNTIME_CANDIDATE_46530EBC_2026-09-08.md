# 固定候補46530ebcの本番用イメージ検証

## 配布物

- ソース: `46530ebc290fed5b41b51ec136eff9943aa31fce`。クリーンな作業ツリーでgit archiveから専用コンテキストを作成。
- archive SHA-256: `fa1cd73b2190c4704754f5e9d8487e03a3e1554bf58f04b8495c90b9f6b7c634`。
- 通常Dockerfileのビルド成功。`tableno-formal-release:46530ebc`、ローカルID `sha256:1148c15382dd48b333f0976efe70aff65cf5ae20d81c072019ccb1a7d3ad8072`。ECRへ未送信。
- accounts/api/scenarios/schedules/support/tableno/templates/staticのPython・HTML・JS・CSS計511ファイルがgit archiveとSHA-256一致。記録はtmp/release-source-hashes-46530ebc.json。フォントのバイナリは下記で別途照合。
- 旧候補10d21e42からのアプリ差分は登録フォームのautofocus除去とテーマフォントの自己配信。OS・依存導入を含む先頭10レイヤーは同一。以前のOS監査の未解決指摘を解消したとは扱わない。

## 隔離検証

初めに非root（UID 10001）・network noneで、同梱19フォントのSHA-256とライセンス、manifest収集後の共通CSS→fonts.css→WOFF2の参照とハッシュを確認。登録フォームのautofocusも不在。最初の検査スクリプトは誤ったsettingsモジュール名で失敗し、manage.pyと同じconfigure_runtime_environmentを使用するよう修正して終了0となった。アプリの変更ではない。

続いて専用internal DockerネットワークにPostgreSQL 18.3とRedis 7を作成し、APP_ENV=aws-prodで通常entrypointを起動した。DB・Redisはtmpfs、公開ポートなし・外向き通信なし。空の合成DBだけを使用し、ソース上書きなし。通常起動のmigrate・collectstatic・Daphne起動が成功した。実Secretsは使わず、S3とCheckoutは無効、worker/beatは起動していない。実OAuth・決済・AWS検証の代用ではない。

| 確認対象 | 結果 |
| --- | --- |
| readiness・登録ページ | HTTP 200 |
| 登録ページの静的参照6件 | ハッシュ付きURLで200、gzip |
| 明示検査30資材 | 既存vendor9件＋テーマCSS2件＋WOFF2 19件のHTTP本文と収集ファイルが一致 |
| テーマフォント19件 | HTTP本文のSHA-256が同梱の出典記録と一致 |
| CSS/JS圧縮 | gzip展開後の内容一致 |
| 登録ページ | autofocus属性なし |
| check --deploy | 終了0・指摘0 |
| migrate --check | 終了0 |
| 後片付け | 所有ラベル照合後に専用app/DB/cacheとnetworkを削除、同ラベルの残存なし |

証跡はGit管理外のtmp/release-46530ebc-build.log、tmp/release-46530ebc-evidence.json、tmp/verify-46530ebc.pyとtmp/runtime-46530ebc内のrun.py・http_probe.py・startup.log・http.log・deploy-check.log・migration-check.log。イメージは追加検査用にローカル保持。実環境・実DB・Secrets・権限・契約は変更していない。

## CIの完了結果

[PR run 34196550690](https://github.com/sheepdog0820/iaia/actions/runs/34196550690)と[push run 34196545815](https://github.com/sheepdog0820/iaia/actions/runs/34196545815)が候補46530ebcで完了・success。PRの全5ジョブの成功と完了ログを確認した。

- Unit / Integration（101965518212）: 1747成功・28省略・159警告、849.43秒、総カバレッジ86.87%。省略を成功件数には含めない。
- production-database（101965518139）: PostgreSQL 18.3の起動をログで確認、284成功・38サブテスト成功・9警告、80.13秒。
- playwright（101965518119）: 3ブラウザ186成功、12.0分。
- system、lint-security: success。後者の成功は別途のOS監査指摘の解消を意味しない。

待機中にGitHub APIが504を返したが、同じrunをGitHub連携で再確認して継続・完了を確認した。テストの再実行や制限緩和はしていない。この記録追加後の文書コミットのCIは別SHAとして扱う。

## 残る公開条件

実RDS/S3復元・実環境の移行/配備/切戻し、外部連携の実サービス検証、OS監査の残指摘、運用・事業判断は未完了。Stripeはユーザー依頼により手動操作待ちを維持する。今回の空DB起動成功を既存DBの復元・切戻し成功とはしない。
