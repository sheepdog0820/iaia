# 背景透過の結果取得・保持削除の競合防止（2026-10-05）

## 再現と変更

[起動応答とworker進行の競合防止](BACKGROUND_DISPATCH_INTEGRITY_2026-10-05.md)および[7b75105e通常配布物](BACKGROUND_RUNTIME_7B75105E_2026-10-05.md)の後続。専用ブランチ `codex/background-result-retention-20261005`、親 `2bac942bd6a4918922b3a76a1363c1e0b22d8cf9` で、結果取得と保持cleanupを検証した。

- APIは所有者条件付きでジョブをロックしていたが、ロック解除後に結果画像を開いていた。cleanupが画像を先に削除すると取得失敗になる。
- 期限後のジョブ・結果削除は古いiteratorのinstanceを使い、行ロック前にstorageを変更していた。待機中に更新された行・画像を削除し、消えた行への保存も起こり得た。
- 結果参照が残っていて実ファイルがない場合や、storageのアクセス拒否・接続障害・read障害は未処理で500になる。

APIでは同じ所有者条件付きの行ロックを、画像全体をHttpResponseへ読み込むまで保持する。ストリーミングへ変更せず、推論も実行しない。結果のopen/read時のOSError・botocore BotoCoreError/ClientErrorだけを捕捉し、非公開cache設定を保った503を返す。DB障害や任意のプログラミング例外はこの捕捉対象ではない。storage障害時もstatus・参照・updated_atを変更せず、後で再取得できるようにする。ログはjob UUIDと例外型だけで、backendの生メッセージやendpointを追加しない。

削除候補ごとにatomic/select_for_updateし、元のstatus・期限・結果参照条件を再評価してからstorageを変更する。更新・削除済みの行はスキップする。別cleanupやAPIのロック待ち後も再評価する。部分削除失敗では、削除できた参照だけを保存し、未削除参照とジョブを保持する。保持期間の基準時刻は延長しない。summaryの候補数は初期選択時点、削除数は実際の操作結果であり、競合時に一致する保証はない。dry-runは従来通り非変更。

結果参照なし・storage取得失敗の案内を「背景透過した画像を取得できません。再度取得するか、もう一度背景透過を行ってください。」に統一した。6版・7版の既存画面はAPI errorを通知に使うため、日本語応答をAPIテストで固定する。テンプレート・JavaScript・レイアウトや、他の既存エラー文言は変更していない。認証・所有者制限・プレミアム制限・日次10回・5MB/4096px制限・結果24時間/ジョブ7日保持・inclusive cutoffは維持する。モデル/マイグレーション変更なし。

## 検証

- 実装前の12テスト：Windows/メモリSQLiteはfailure1・error5・PG専用5省略、隔離PostgreSQL18.3はfailure5・error5。古い期限snapshotによる削除、欠損/障害の500、実際の行ロック待ち前のstorage変更を再現した。最初の修正後はPG12件成功。
- 新規20テスト：結果参照/実ファイル欠損、storage AccessDenied/接続/read障害、汎用応答とログの秘匿、時刻保持、古い期限/status/削除済みsnapshot、部分削除失敗、空の終端ジョブ、24時間/7日境界、古いactive選択の再確認、実PGロック6ケースと観測なしを失敗させる診断テスト。
- PGでは別thread/connectionとpg_blocking_pidsで、結果の実read中にcleanupが待機することを確認した。ジョブ削除/結果削除の両方を含む。別の更新transactionの待機後は最新期限で削除をスキップする。同時cleanup2件ではstorage結果削除は1回だけ、削除成功数の合計1・失敗0。時間待ちだけをロック成功の根拠にしていない。
- 最終Windows/メモリSQLite：122件中111成功・PG専用11省略、18.089秒。最終隔離PG：122件全成功・省略0、23.184秒。先行finalization15件・dispatch13件・既存API25件・model6件・infrastructure4件・release documentation39件を含む。
- 拡大試験の途中、実readの待機を挿入する補助コードがFile.readのread-only propertyへ代入し、PG119件中2 failureとなった。この失敗を成功扱いせず、File subclassでreadを上書きする補助コードへ修正した。待機上限・合格条件・ロック観測を緩めていない。日本語応答は変更前の5 failureを確認後、上記最終回帰で成功した。

| coverage対象 | 文 | 分岐 | 実行率 | 除外 |
|---|---:|---:|---:|---:|
| cleanup_background_removal_jobs | 50 | 26 | 100% | 0 |
| CharacterImageBackgroundRemovalStatusView.get | 18 | 6 | 100% | 0 |
| 新規integration test | 290 | 18 | 100% | 0 |

coverageは変更2関数と新規テストの範囲で、全アプリの100%を意味しない。Python3.11.1で変更Python3ファイルのBlack/isort/Flake8成功、Bandit指摘0・解析エラー0、差分空白検査成功。実diffを所有者制限、ロックとstorage操作順、状態/時刻の保持、限定した例外捕捉、非公開cache、期限境界、部分失敗、テストの判定条件から自己レビューし、当該差分の追加要修正指摘なし。

文書追加後のrelease documentation39件も成功（0.036秒）。証拠6hash一致、変更文書2件の相対リンク193件欠落0、staged6テキストのUTF-8/LF/BOM/置換文字と空白差分の検査も成功。

ソース検証は、7b75105eの既存runtime imageに今回のrepositoryをread-only mountした実行であり、今回修正の通常配布物検証ではない。coverage7.15.4のみread-only mountし、pure Python tracerを使った。SDK/native依存は差し替えていない。PGはnetwork none・256MiB上限・使い捨てtmpfsの専用container、テストは合成user/画像と一時mediaのみ。起動要求/推論/storage障害はmockを含み、実ECS dispatch・S3・実モデル・AWS性能の成功に拡張しない。

## 残条件と承認境界

DBとS3の分散原子性、DB commit失敗後のstorage整合性、外部/手動のファイル削除、削除済み行の孤立ファイル回収、S3遅延・障害時の性能/長時間運用は未証明。結果read中はロックを保持するため、同じジョブのcleanupはstorage読取時間だけ待機する。実AWSのp95合格を主張しない。pendingの曖昧なdispatch、worker常設運用、他の画面エラー文言、実課金/外部連携/OS/nativeゲート等も残る。

親2bac942bの[CI 37322521241](https://github.com/sheepdog0820/iaia/actions/runs/37322521241)はhead SHAと照合し、全6項目successを確認した。今回候補の全CI・通常配布物・新規OS監査・AWSは未確認。Production Databaseの明示対象へ新規integration testを追加し、通常push後に固定SHAでCIを観測する。pushのworkflowはCIのみでAWS反映を起動しない。

今回main・AWS/ECR/ECS/S3/CloudFront・共有DB・実データ・Secrets/IAM・実課金/通知・常設容量/継続費用を変更していない。元checkoutのハンドアウト関連13変更を保持した。完了済みアイコン8567f49fの承認や固定6b6c570cの反映案へ追加しない。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goを維持する。未反映なので実環境の切戻しは不要。作業ブランチの当該修正はrevert可能だが競合を再導入するため、安全な修正版を優先する。

## 証拠

証拠は `C:/tmp/iaia-background-result-retention-20261005/` に保存。専用PG container IDは `f1c8de4675d2bb752f40061c8556fb59cc9e82bb930ec216768cbfb19bef9590`。終了時にID/network none/tmpfsを再照合して停止・自動削除し、使い捨てDBを破棄した。合成媒体は各テストのTemporaryDirectory cleanupで削除、失敗ログを含む証拠は保持する。

| ファイル | SHA256 |
|---|---|
| sqlite-red.log | 82fafb86ae96d684bd7fbb6d678d4a87942a118be34e5fff076ff7a9f25dc1c9 |
| postgres-red.log | 7e7f95c621755de39e4ba21fd4b5d10fcc0c79bce96f415e696aafe9e7d268ea |
| sqlite-reviewed.log | aa1a44e88cded354289f7e061168388d3c7016f3934a9725141bc2b54e1d142a |
| postgres-reviewed.log | fb6b916bd1eea8789422e16b39cd7c4052c3d96829343bb72e2650ae9225ec5f |
| coverage-reviewed.json | 7ace083adc769da279253e16141d448632bf1f3a80c940cfc38274d4be155c38 |
| bandit.json | 75d595bbee8bb7601309ab30f5ce8391086add23ef48a530a2bfb200f19ea611 |
