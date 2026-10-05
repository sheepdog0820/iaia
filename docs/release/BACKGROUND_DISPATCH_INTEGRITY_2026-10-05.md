# 背景透過の起動応答とworker進行の競合防止（2026-10-05）

## 再現した問題と修正

先行c0b5380bの[終端状態保護](BACKGROUND_JOB_FINALIZATION_2026-10-05.md)に続き、Webの起動要求とworkerの進行が重なる経路を隔離環境で検証した。

- ECS起動要求の応答が例外になった時、Webが古いpendingのinstanceを使って、既にrunning/completed/failedのジョブを起動失敗へ上書きする。
- PostgreSQLの行ロックを待つ前に、同じ例外処理が元画像を削除する。
- 起動要求中にジョブが削除されると、存在しない行へのsaveで500になる。
- 成功した起動応答のtask ARN保存がupdated_atを更新し、workerのタイムアウトや完了結果の24時間保持の基準時刻を延長する。Webの202応答にも古いpendingが残る。

例外処理は、所有者条件付きで同じジョブをselect_for_updateし直す。まだpendingなら従来通り汎用起動失敗・元画像cleanup・503とし、running/completedは202と現在のstatus/status URLを返す。既にfailedならその理由を保持した503、削除済みなら404とする。workerが進んだジョブの状態・画像・時刻を例外処理で更新しない。

成功した起動応答では、同じinstanceを行ロック/refreshしてtask ARNのみ保存する。updated_atを変更せず、呼出し元も最新statusになる。ネットワーク要求自体は行ロック外で行う。ECS task定義/ネットワーク/単発workerコマンド・認証/所有者制限・プレミアム制限・日次10回・元画像5MB/4096px制限・24時間/7日保持は変更しない。DBモデル/マイグレーション変更なし。

## 検証

- 実装前の新規9テストでWindows/SQLiteは6 failure/2 error/PG専用1省略、隔離PostgreSQL18.3は7 failure/2 error。完了の巻き戻り、失敗理由の上書き、消えた行の500、時刻更新を再現した。
- PG専用テストでは別connection/threadとpg_blocking_pidsで行ロック待ちを観測し、待機中の元画像削除を修正前に実際にassert失敗させた。修正後は元画像/結果/最新completedを保持し、202でstatus URLを返す。先行のロック観測helperを再利用し、観測なしを成功扱いするfallbackや時間上限延長は追加していない。
- 新規13テスト：応答消失後のrunning/completed/failed、削除、元画像なしのpending起動失敗、upload未指定/サイズ超過、起動設定なし、成功応答の最新状態、completed/runningの時刻保持、消えた行へのtask ARN保存拒否、実PG行ロック。
- 最終Windows/メモリSQLiteは102件中98成功・PG専用4省略、15.428秒。隔離PGでは同じ102件全成功・省略0、17.441秒。先行finalization15件・既存API25件・model6件・infrastructure4件・release documentation39件を含む。
- 初回の拡大回帰では存在しないモデル試験名を指定し、54件の実行がimport error1で失敗した。成功扱いせず、正しいtests.unit.test_background_removal_modelを含む上記102件で再実行した。初期環境設定の不足による実行前エラーも再現試験の失敗数へ含めない。
- coverageは変更2関数のstart_background_removal_task 16文/4分岐、CharacterImageBackgroundRemovalView.post 44文/18分岐を全実行、合計60文/22分岐100%。新規テスト198文も100%、分岐0、除外0。全アプリ・全moduleの100%ではない。
- Python3.11.1で変更Python3ファイルのBlack/isort/Flake8成功、Bandit指摘0/エラー0。新しい利用者向け文言はなく、既存API文言を移動・維持した。日本語画面の本文/導線/表示は変更していない。

ソース検証は先行c7390ee3 runtime imageに今回ソースをreadonly mountした実行であり、今回修正の通常配布物検証ではない。coverage7.15.4のみreadonly mountしたpure Python tracerを用い、SDK/native依存は差し替えていない。PGはnetwork noneの自前container・使い捨てtmpfs・合成user/画像のみ。boto3の起動要求と推論はmockであり、実ECS/S3/モデル/AWS性能の成功を意味しない。

## 残条件・承認・復旧

ECSが受理したがworkerがまだpendingのまま応答だけ失われた場合は、引き続き起動失敗とする既存挙動が残る。ECSの冪等dispatch/状態照会/再試行を実装・実環境検証した変更ではない。削除・所有者変更後のstorage孤立ファイル回収、DB/S3分散原子性、結果取得と保持cleanupの競合、S3遅延・障害も未証明。今回の状態保護を背景透過の全経路合格へ拡張しない。

今回候補の通常配布物・全OS監査・全CI・AWSは未確認。親c0b5380bのCI [37317470226](https://github.com/sheepdog0820/iaia/actions/runs/37317470226)はこの記録作成前の照合でin_progress、成功判定していない。Production Databaseの明示対象へ今回のintegration testを追加し、push後に固定SHAでCIを確認する。

main/AWS/ECR/共有DB/実データ/Secrets/IAM/実課金/実通知/容量は変更していない。元のハンドアウトworktreeの無関係な13変更を保持する。完了済みアイコン承認と固定6b6c570cの反映案を今回候補へ転用しない。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goを維持する。未反映なので実環境の切戻しは不要。作業ブランチの当該修正はrevert可能だが競合を再導入するため、安全な修正版を優先する。

実diffを状態遷移・権限・消えた行・storage操作のロック順・例外時応答・期限保持・テストの判定条件で自己レビューし、当該修正の追加要修正指摘なし。残条件は上記の通り成功扱いしない。文書追加後の39テスト成功、証拠6hash一致、変更文書2件の相対リンク190件欠落0、stage6テキストのUTF-8/LF/BOM/置換文字検査と空白差分検査も成功。

## 証拠

証拠はC:/tmp/iaia-background-dispatch-20261005/に保持する。事前に記録したPG container ID `4bfff9987bda921af7519266f6a7033e4c1edea91c12d1245458f82b1697abee`・network none・tmpfsを終了前に再照合し、停止・自動削除を確認した。使い捨てDB/媒体は破棄済み、証拠ログは保持する。

| ファイル | SHA256 |
|---|---|
| sqlite-red.log | 68f645918916ef42c1065018cd5ad09b42b27f7ffa57c5a7ba0c94a53f1b219d |
| postgres-red.log | be914f0bf1d85f194473d8c79a39e8d418042759a366afee8d6709c223f4f2b1 |
| sqlite-final.log | a5fa5e3351e5806640105bed055610fef49991cdc94866d31ce2bda51456ac19 |
| postgres-final.log | 7feae67b78fc4483009faed2b796fed745247864407ba5a1a4c21a13a1c05f3a |
| coverage-pg.json | 1cf9a84551f20c91ee85947c0905c5f3ec2bbd0b913a4ca61e678d7ed152d43d |
| bandit.json | 6474ca071f318e4f207e0fc27ebf0398cddffdf377a6ae00d7fcfcfe8b5f8276 |
