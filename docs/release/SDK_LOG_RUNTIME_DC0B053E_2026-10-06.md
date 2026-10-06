# SDKログ保護：通常配布物・実HTTPでの資格情報障害検証

## 固定対象・配布物

対象は `dc0b053e356e2e9d1426f60760d07257c3e198e0`（[SDKログ修正](SDK_LOG_PRIVACY_2026-10-06.md)）、記録ブランチは `codex/sdk-log-runtime-20261006`。固定git archiveを通常Dockerfile/.dockerignoreでbuildした。ローカルtagは `tableno:sdk-log-runtime-dc0b053e`、image IDは `sha256:d90ce57ac458676631e77e4f66f4e023553406901dd5b97d0aeb77bd4a717f04`、revision labelは上記full SHAに一致する。

683選定source/assetsの集合・全ハッシュとentrypoint実体をarchiveに照合し、差分0・Python cache0を確認。先行b3496898の実イメージと111パッケージの名称/版・最初の依存10層が一致した。SDKは配布物のboto3/botocore **1.43.80**（先行Windows source検証の1.43.34とは区別）。依存build段階はすべてCACHED、アプリ/SDK/coverage overlay・追加pip installはない。HTTP harnessだけを/app外へmountし、アプリ/SDKのpatch・差替えは行わない。元checkoutの未コミット13項目は含めない。

初回比較は旧runtime-manifest名と旧inspection構造を誤指定して終了1。部分的な `distribution-check.json` を成功証拠にせず、先行実イメージをread-onlyで再読して `distribution-check-corrected.json` に訂正した。683選定ファイル一致は配布物の全ファイルやnative build閉包一致を意味しない。

## 隔離・回帰

PostgreSQL18.3（image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`）はnetwork none・公開portなし・256MiB・512MiB tmpfs。Web/fake/probe/workerはそのnetwork namespaceのloopbackだけを共有する。実AWS/IAM/Stripe/SMTP/S3は接続せず、すべて合成設定・使い捨てDB/mediaで実施した。

| 試験 | 結果 |
| --- | --- |
| 初回一括回帰 | 252件、failure1/error1、98.092秒・終了1。隔離用USE_REDIS_CACHE=false/EMAIL_HOSTが既存settings試験の想定と衝突 |
| 訂正後PG回帰 | 背景透過/画像/有料権限13 moduleと新SDK6件、191成功/省略0、64.862秒・終了0。既存の実PG lock16件を含む |
| 訂正後settings/アクセスログ回帰 | 別の合成settings環境で67成功/省略0、40.220秒・終了0。DB不使用 |
| テスト環境訂正 | アプリ修正なし。191と67はSDK6件が重複し、252種類の試験を別々の環境で検証した |

Webは通常entrypoint・aws-pre/DEBUG=false、0.25CPU/512MiB、read-only root、static/tmpだけtmpfs。使い捨てDBにmigrate、collectstaticは232 copied/624 post-processedで成功。初回の30秒readiness待機は期限に達したが、同じコンテナのmigration進行・稼働を確認して待ち、再起動せず後続readiness200を確認した。初回全成功とは報告しない。

## 実HTTP・SDK警告

既存の[資格情報障害harness](BACKGROUND_SIGNING_RUNTIME_B3496898_2026-10-06.md)を再利用。実HTTP/DRF Token/通常serializer・署名・SDK retryを通し、ECS/資格情報サービスだけがloopbackの合成wireである。APIClient/force_authenticate/SDK mockはこのHTTP検証では使用しない。

- `refresh_fail`：先行500後に資格情報更新応答を400へ変更。wire1回、資格情報失敗3回、pending202・source bytes・updated_at・job ID保持。重複409は追加wireなし。
- `initial_credentials_fail`：wire0回・資格情報失敗3回、既存の確定失敗503・source削除。SDKの共有資格情報状態を利用した試験で、実IAM初回認証や新processの挙動の証明ではない。
- `retry_refused`/`retry_task_failure`：先行500後の400/HTTP200+failuresでもwire2回・pending入力保持。初回拒否/初回task failureはwire1回・既存503。
- `recover`：先行500後の200はwire2回、同一token/parameters・source/updated_at保持・task ARN保存。
- 全体wire9回・資格情報16要求。所有者外404/未認証401、非premium日本語403・副作用なし、readiness200、no-store/Vary Cookie/Authorizationを維持。
- 16分経過させたretry_refusedを既存cleanupでtimeout failedにし、source削除・status503を確認。期限・quota・料金・権限の変更なし。

prepare38・completed3・finish3、合計**実HTTP44確認**が成功。応答本文にECS/資格情報の合成非公開markerはない。この件数は成功したharness確認であり、起動待機の全HTTP要求数ではない。

Web最終ログはcredential logger2件・WARNING2件・CredentialRetrievalError2件・`_protected_refresh`コード位置2件を保持。資格情報応答本文、ECS応答本文、合成access/secret/session値、raw traceback見出しはすべて0件。先行b349では資格情報本文4出現を観測していたが、今回は通常配布物の実SDK警告でも出力されなかった。SDKを無効化したり警告閾値を引き上げたりした結果ではない。

対象は設定済みstream/file/root経路であり、後付けhandler・SDK以外のlogger・Sentry等の独立収集経路、実Secrets流出や過去CloudWatch監査までの証明へ拡張しない。mandatory/advisory自由文そのものは安全な要約に置換する。今回の実HTTPはmandatory障害で、advisory挙動は配布物の新SDK unit testで検証した。

## 実推論・再実行・後片付け

同じ通常イメージ/entrypointのworkerを1CPU/2GiB・read-only root・512MiB tmpfsで実行。既存U2NETをread-only mountし、model SHA `8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491` を確認した。ONNX telemetry opt-outを維持し、外部downloadはない。

refresh_fail jobの実透過が終了0でcompleted、128x128 RGBA・alpha extrema 0/255、PNG SHA `97118d98655762cab2a06137caeeba448a79f62b8cb7eacbd42f7b066c356cde`。実HTTPでPNG bytes/Content-Type・他所有者404/未認証401を確認。モデルmountなしの再実行は終了0で時刻・filename・hash不変。期限切れretry_refused再実行は既定のCommandError/終了1で、時刻不変・出力なし・追加wireなしだった。

cleanup前に合成prefix8ユーザー・7 job UUIDの完全一致を確認し、それだけのfile/job/user/tokenを削除。独立SQLでもusers/jobs/tokens0、media file0、test DB不存在を確認。own label/ID/network/ports/OOMを検査してWeb・fake・worker・PGのみ停止/削除し、残存ownコンテナ0。全OOM=false。PG tmpfsは破棄したが、証拠・archive・harness・model・新Scout cacheは保持し再生成可能。元のユーザーDB/fileは操作しない。

## 新規監査・CI・公開境界

新規cache/tempで既存Scout **1.26.0**（git ee73e17cd5243bd85c30416b274c339ad5e2f284）を用いた全OS監査は292 packages、16 vulnerable packages、39指摘（HIGH3/MEDIUM1/LOW35、Python0）、終了2。先行SARIFのCVE/severity/package差分0。HIGH `CVE-2026-102010` / `CVE-2026-95619` / `CVE-2026-85091` は未解消・未受容である。Python0やsource一致をnative閉包/HIGH解消にしない。

[候補CI37397258941](https://github.com/sheepdog0820/iaia/actions/runs/37397258941)のhead SHAはdc0b053eに一致。10:15 JST照合ではlint-security/system/infrastructure/production-databaseの4項目success、Unit/Integration・Playwrightの2項目in_progress。全6成功や全体coverage合格とは報告しない。

本ターンは文書2ファイルだけの記録変更で、main・AWS・共有DB・Secrets/IAM/容量/費用/外部通知は変更しない。main読み取り照合は8567f49fのまま。実AWS/S3/IAM・常設worker・実課金/外部連携・性能/復旧/法務等は未達で、既存アイコン承認へ追加せず正式公開No-Goを維持する。共有反映するなら対象コミット・現在の稼働定義・復旧方法を別途確認し、承認された範囲だけで行う。

記録の文書39テストは0.036秒・終了0、相対参照206件の欠落0、証拠表18ハッシュ一致、staged2ファイルUTF-8/LF・BOMなし・差分検査成功。最初のハッシュ表検査regexがunderscore名2件を拾わなかったため訂正し、全18件を再照合した。自己レビューで固定版/overlayなしの範囲、重複テスト数、実HTTPとunitの区別、ログ抑制でないこと、初回失敗・CI/OS未合格・後片付け境界を確認し、追加指摘なし。画面変更/新利用者向け文言はなく、ブラウザー検証は行わない。

## 保持証拠

保存先は `D:/tmp/codex-tableno-sdk-runtime-dc0b053e-20261006/`。検証側失敗も保存している。

| ファイル | SHA-256 |
| --- | --- |
| build.log | 0e2927e65d9e8702e8bf7780a622a0a638285dc28b4f33c5bfe105af35543aba |
| distribution-check-corrected.json | c1d2dfec7d05cd002aeac9ec3b116b628ca43cbecec9c9177d538093bdc54651 |
| regression-runtime.log | 256977ec341dd601d4ca63fbd1ef5ea5a8542663d6146823a4f1dace954653a1 |
| regression-pg-corrected.log | b21d0d523bb653253e500a82979c1ec880eb0c05f0a83c83eb455fd9470777bd |
| regression-settings-corrected.log | 5eca1a3c3e2977a93034f748a3f5b0307656c4362a9af66963863aec90e37c77 |
| http-prepare.log | 5978d903d4d3ec66baa2b60379acaaddb4afd28858660fb11af56644b2491965 |
| http-completed.log | 3308494db0a41d6ace397ea9366b245cb9f934b28949531fe5f5d29e4eec7548 |
| http-finish.log | af91ec552aa651f2399f52c466d4678076862e8a6cb9a624e878b47a56bf46dc |
| http-state.json | eb67a98ebcadaab5de41513f18e190eaa4ea17a58b60df3448d2f99f5b1837f9 |
| fake-ecs-state.json | 8805b4e5512e59e0c69367beb3a3482b3dd9ff5d832ab544c6d65357561fbbce |
| web-final.log | 971f66c72d77a38174d155843e8e0040da373f7c61e5499825a26e454d33b176 |
| web-log-check.json | 0be501391e01bcaa477559147b29a8e0dbb908693bd926399145dc4d61b41f8f |
| worker-success.log | 1af345998923254d768a65fa2bb307af9fb5471fc288c29eea4b89a855dec7f6 |
| worker-reentry-refresh_fail.log | 1af345998923254d768a65fa2bb307af9fb5471fc288c29eea4b89a855dec7f6 |
| worker-reentry-retry_refused.log | e819a9dbcc615ef08722202a25cccd1adf439d8e4cade8c9f56b72b4a818b47d |
| scout.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| scan-summary.json | 312038b9341d9fb4ce4a21f61442c052ce5e747ec5817b5e6d3d432960d65236 |
| runtime-containers-final.json | 97c53be5c14420717ca09306af9112ff6943c6469853061f9bbed2d247c8eb6c |
