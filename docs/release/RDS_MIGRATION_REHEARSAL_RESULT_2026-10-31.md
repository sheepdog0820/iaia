# 非公開RDSコピー内の4移行リハーサル結果（2026-10-31）

承認されたd664bb40/a85によるコピー内移行と後片付けは成功した。正式公開は **No-Go**。共有DBの適用、Web/worker反映、mainマージは実行していない。[集計証跡](RDS_MIGRATION_REHEARSAL_EVIDENCE_2026-10-31.json)に対象・時刻・検証値・ローカル証跡のSHA256を保存した。

## 対象と実行結果

| 項目 | 実結果 |
| --- | --- |
| 固定source / image config | `d664bb403fee45873b14e0da8b808a2607adc638` / `sha256:a85b0dbf62ab838e1b67465fa2c35322b2e86cf285f688d3293287a72d2f0bc0` |
| ECR / 実task manifest digest | 両方`sha256:02776b5b2f570af43ff50bc196dfe228b0e38c9e54951e4e20ef208da5370fc6`。config digestもlocal image IDと一致 |
| コピー | 保持snapshotから`tableno-migration-rehearsal-20261031-a`へ復元。PG18.3、非公開、既存KMS、専用SG |
| 単発task | `33f725f703a44d3f8a113c5d87e562ef`、0.25 CPU/512 MiB、UID10001、root read-only、task roleなし。DB_PASSWORDだけを既存execution roleで注入 |
| 時間（JST） | DB復元要求15:19:22、task開始15:28:54・処理終了15:29:01・停止15:29:26、全cleanup確認15:41:29。task15分/clone2時間の運用目標内 |
| 適用 | accounts0065〜0068の4件。TLS/startup READ ONLY、コピー専用の接続先・DB名・利用者を確認後に適用 |
| 技能 | 6版190行・7版48行を比較。bonus→other合算以外の変化を拒否する検証が成功 |
| 課金/監査 | 対象の購読・監査行は各0。非空の実課金行の保全を実証した結果には含めない |
| 適用後 | 新3表は空、移行履歴4件追加、全アプリ計画は空、未知履歴0、既存重複総数維持、再接続後READ ONLY/TLSを確認 |

単発taskはexit0で終了し、CloudWatchの出力は検証済みの集計JSON1件だった。業務行・個別データの指紋・秘密値をログやローカル出力へ保存していない。行比較はtaskのメモリ内で行った。TLSは`sslmode=require`による暗号化で、verify-fullの証明書/hostname照合ではない。

4移行と適用コマンドの5ファイルは、後続候補854c15c0でもbytes一致を確認した。実AWSで実行したimageは承認されたd664/a85であり、後続の画像API修正を含む854/f77を実行したとは扱わない。

## 後片付けと読み取り応答の補正

承認済み17手順を記録した。StopTaskは同じtaskが既にSTOPPEDだったため確認のみで、実際の変更SDK呼び出しは16件。固定imageの専用tag送信は別に実施した。定義はINACTIVE、専用RDS/自動backup/clone snapshot/SG2件/ENI/専用ECR tagは不在を実APIで確認した。

準備helperは、削除済みDBの自動backupに対する`DBInstanceAutomatedBackupNotFound`を未処理だった。[AWS公式仕様](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_DescribeDBInstanceAutomatedBackups.html)と、同じDbiResourceIdの実404応答を照合して不在を確認した。元のreview/executor/probeを変更せず、読み取り処理を補ったcleanup補助から、残る承認済み入力だけを実行した。SGの相互参照解除後に残る承認済みHTTPS/DNSルールは、当初の計画どおりSG削除で消去した。解除ガードの修正で操作入力・対象・範囲は変更せず、実行済み操作の再実行もしていない。

元snapshotは非公開・暗号化のまま保持する。実取得は10月30日08:12:13.770 JST、保管見直しは11月6日同時刻以降。移行未実施・未検証等で必要なら削除しない。集計ログの既存保持規則3日は変更していない。

承認予算案は2 USD、事前概算は約0.067 USD＋ログ・税等。実請求額は未確認で、2 USDを請求の強制上限とは扱わない。

## 共有環境と残作業

15:44 JSTの事後読み取りで、元RDSは18.3/available・暗号化・非公開、Web定義55・従来digest6d4050ec、readiness200/DB-cache okを確認した。共有移行履歴を再取得した検査ではない。最新の共有SQL計画の記録は10月30日21:29 JSTのままである。

切替直前の全writer確認/停止、新しいbackupとデータ差分の再照合、統合候補の共有DB適用/Web・背景処理反映、実Stripe/OAuth/外部配送、DB/S3切戻しとRPO24h/RTO4h、性能・監視・OS/native指摘・利用者への運用条件は未完了。この古いsnapshotのコピー移行だけを、DB/S3全体復旧や正式公開の合格にしない。[全25条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md#判定表)を維持する。
