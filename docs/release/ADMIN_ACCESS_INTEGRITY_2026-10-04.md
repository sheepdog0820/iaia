# 管理画面の停止・復旧・返金確認の整合性（2026-10-04）

## 対象と再現

先行 `c9f3e783` を基準に、課金レコード管理画面の `revoke_selected_access`、`restore_selected_access`、`mark_refund_or_dispute_reviewed` を専用ブランチ `codex/admin-access-integrity-20261004` で検証した。[先行の再同期修正](PREMIUM_RECONCILIATION_INTEGRITY_2026-10-04.md)と同様、選択時の古い取得結果を使う経路が残っていた。

復旧では、その後に解約された権限を付与したり、有効化された権限を停止できた。返金確認は古い検知時刻/sourceを監査へ記録し、すでに確認済みでも重複監査を作った。停止も古いsourceで監査を作った。3操作とも、監査保存に失敗しても権限/失効情報/検知の変更が残った。

修正前SQLiteの初回8メソッドは終了1。削除候補を同じTestCase内のループで試したため、後半2件は先のDatabaseErrorによるトランザクション破損の影響を受けた。削除3操作を独立テストへ分離して再実行し、それぞれ `Save with update_fields did not affect any rows` の3エラーを再現した。この試験側の修正とアプリ修正を区別する。初回のSECRET_KEY不足は試験開始前の設定失敗であり、REDに数えない。

修正前のPostgreSQL専用3件は全失敗（30.735秒、終了1）。競合する合成writerが課金行をロックしている間、どの管理操作も共有FOR UPDATEへ到達しなかった。実Stripe API/実Webhookを使った競合の証拠ではない。

## 修正と仕様の維持

- 選択対象のIDをpk順に取得し、対象ごとのtransaction内でPremiumSubscription行をロックして最新値を読む。購入完了・コード利用・失効・再同期と同じ課金行で直列化する。user JOINを含めず、userのフラグもロック取得後に読む。
- 保存と監査を同じtransactionにし、監査失敗時はその対象をrollbackする。複数対象では先に成功した対象を保持し、失敗時に成功メッセージを出さない。処理件数の加算は対象transactionの終了後。
- ID列挙後に消えた課金行はスキップする。返金検知の有無もロック後に判断し、最新検知時刻を監査へ保存する。すでに確認済みなら件数0・重複監査なし。
- 停止/復旧は明示的な運営操作であり、繰り返しも従来どおり監査へ残す。停止は選択した現在の課金行を停止する意図で、新しい状態を自動保護するコード由来失効処理とは異なる。
- 復旧はrevoked_at/reasonを解除して再同期する既存仕様を維持する。subscription_statusがrevokedならactiveへ変更しない。手動付与の既存override判定を保持する。Stripe契約の解約・復活・価格・税設定は操作しない。
- actor/source/reason/metadataと日本語の件数表示を保持する。新規16テストをPostgreSQL CIへ追加し、SQLiteで省略される専用行ロック3件をPGで必須実行する。

Stripe監査スキルの方針に沿い、Webhookによる権限付与を購入戻り画面での付与へ変更していない。SDK/APIバージョン、Secrets、税設定、課金有効化の変更もない。

## 最終検証

| 環境 | 重複しない広い回帰2実行の結果 | 時間 |
| --- | --- | --- |
| Windows Python3.11.1 / Django5.2.17 / SQLiteメモリDB | 251件中233成功・行ロック18省略 + 別89成功 = 322成功・18省略 | 42.098 + 1.494秒 |
| Linux / 隔離PostgreSQL18.3 | 254 + 別89 = 343成功・省略0 | 37.675 + 2.419秒 |

範囲はbilling・既存課金競合・paid_feature_lifecycle・コード利用/失効/再同期、退会ガード、課金メール配送/監視、Invoice/Event/Checkout/Disputeの順序・再試行・復旧・複数停止理由・Portal解約。エラーログは異常系試験の期待結果で、予期しない試験エラーはない。SQLiteの省略を成功件数に含めない。

最終の新規16件と既存管理画面36件はPGで52件成功（3.023秒、省略0）。SQLiteは新規13件と既存36件の49件成功（0.925秒）。これらは広い回帰と重複するため、343/322件へ再加算しない。最新状態・共有課金行のロック待機・監査失敗時の全フィールド/権限rollback・削除候補・最新検知・明示操作の繰り返し・manual override・revoked状態・複数対象のpk順と失敗対象だけのrollbackを確認した。

coverage7.15.4のPython/thread tracingで、変更3メソッドは停止11文/4分岐、復旧18文/6分岐、返金確認13文/4分岐がそれぞれ100%。新規テスト234文/22分岐も100%。admin全体や全権限経路の100%ではない。JSON解析の初回はPowerShellが空名のfunctionsキーを拒否したため、AsHashtableで読み直した。試験/coverage生成は成功しており、解析失敗を成功として扱っていない。

Black/isort/Flake8、Bandit対象2ファイル（0指摘・0解析エラー）、Django check・makemigrations --check --dry-run（変更なし）、workflow YAMLとPG対象指定、UTF-8/BOMなし/LF/置換文字なし、差分空白検査を確認した。source・共有ロック順・更新対象・監査原子性・件数・日本語表示を自己レビューし、この修正単位に未解消指摘はない。

## 環境と証跡

DBは公開ポートなし・network none・512 MiB・データtmpfsの専用PG。テストworkerだけがPGのnetwork namespaceを使用した。合成SECRET_KEY/利用者/課金IDとENV_FILE空・APP_ENV=local・locmemメール/cacheを用い、共有DB/Secrets/実ユーザーを参照していない。

先行通常イメージ `sha256:46795320922764a1bc2065f8c161e8d317cb0f2f5c1588a6d9026660d4a666f4` を工具として使い、今回ソースをread-only mountした。この実行を修正後の通常配布物の証明にしない。coverageも既存の工具をread-only mountした。テストDBはDjangoが破棄し、今回専用PGもIDを再照合して停止・削除した。合成DBデータはtmpfsとともに破棄され、再作成可能。証跡と合成設定は `C:/tmp/iaia-admin-access-20261004` に保持する。

| 証跡 | SHA-256 |
| --- | --- |
| coverage-pg-final.json | cc6849bab2bb2274df99ae76c94e2bc42b1991e177de73a784f810ada4e7dd56 |
| bandit.json | 0d2b623e98e1624e4cdfe99bb554484608f98b110adf7b184016b4c515519a7f |

## 残作業・反映境界

先行 `c9f3e783047847b208bc2955658de42cdc385293` の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37190166680)を今回読み取り照合した。確認ダイアログのCI不足は限定的に解消したが、以前のWebKit開始遅延の原因確定・通常配布物・AWS合格には拡張しない。今回の候補CI/通常配布物/AWSは未確認。

CustomUserAdminの直接編集・課金inline/direct form等の別経路、実署名Webhookとの競合、外部連携実運用、OS HIGH2件を含む正式公開条件は残る。mainは読み取りで8567f49fと確認。今回main・AWS/ECR/ECS/S3/CloudFront・共有DB・実データ・Secrets/IAM・課金有効化・容量/継続費用を変更していない。元checkoutのハンドアウト差分を保持し、固定反映案6b6c570cの承認範囲を拡張しない。

復旧はfix-forwardを優先する。今回コミットだけを作業ブランチでrevertすることも可能だが、誤付与/停止・監査欠落を再導入するため、旧版をそのまま公開しない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
