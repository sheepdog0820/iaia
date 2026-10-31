# 最新候補・未完了作業・承認の整理（2026-10-31）

正式公開は **No-Go**。有料プランと外部連携を含む[受け入れ表](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md#判定表)のF/B/I/Q/O全25条件を維持する。限定した検証結果を行全体や正式公開の合格へ広げない。

## PR54統合後の現在地

- 承認された[PR #54](https://github.com/sheepdog0820/iaia/pull/54)を通常マージし、mainは`9f3ccde7717654dd9f9e53241e1e10c7e3f37de4`となった。merge treeは検証head`3e93050e`と一致する。旧PR46〜53の内容はmainに入り、47〜53は重複候補として閉じた。個別のcodex親ブランチへはマージしていない。
- マージ後の同一SHAで全7チェックが成功した。アプリ側6チェックとGitHubの依存グラフ更新であり、マージ前のPR/push計12チェックとは数え方を分ける。全体2,417成功・129省略、PG690成功・361 subtests/省略0、Playwright243成功、system14成功を確認した。
- main54の通常配布物は`sha256:8b047285377d1f5e98288f9d63832300c0c0e0cf9adad98f163ff17e445831dc`。PG164件と実111依存監査0件を確認済みで、F02の新しい0069や所有権APIを含む検証結果ではない。OS52指摘・exit2、共有DB/Webへの未反映は残る。
- F02の所有権移譲は人間が推奨仕様を採用した。[仕様・移行・復旧条件と限定検証](GROUP_OWNERSHIP_TRANSFER_SPEC_2026-10-31.md)に従い、main54からの専用ブランチで実装した。関連PG143件・99 subtests、移行関連PG43件・46 subtests、通常登録からの所有権移譲と元作成者退会の3ブラウザー操作が成功。変更Python実行行381/381を確認した。通常配布物・最終CI、Draft PR、main統合・共有0069・AWS反映は未完了。管理者追加やゲストclaimだけでF02完了とはしない。
- 承認済みの実AWSコピー内4移行リハーサルと後片付けは完了済みで、再実行しない。共有適用前には最新の全体計画・backup・全writerの停止・配備と復旧を具体化する。0069を既存の4移行の承認へ追加しない。

以下はPR54統合前の調査・候補・計画の履歴である。候補の「未統合」「回答待ち」、F02の「未実装」「範囲判断待ち」は当時の状態として保持し、現在の残作業へ重複計上しない。稼働AWSの記録を最新の再検査と読み替えない。

## main・稼働版・候補の対応

| 対象 | 確認できた状態 | 残る差分 |
| --- | --- | --- |
| main | deddd772。承認済みPR #37まで | lockはTwisted26.10.0rc2。追加候補は未統合 |
| 稼働Web55 | 2026-10-31T06:44:19.041805+00:00の実task digestは`sha256:6d4050ec19ba5d34740643d515436baa5dd27b99a912b9c20ad7a9af0812af06`、256 CPU units/512 MiB、desired/running1・pending0 | 同じimmutable artifactの既存ローカルmetadataでTwisted26.4.0/Stripe15.5.1/pyasn1 0.6.4を照合済み。全sourceのGit同一性や全依存監査の証明ではない |
| 固定候補 | source `854c15c05a4b566adfacb072625781d376f405de`、通常image `sha256:f77c1ca6733ba33b7c13f8ed46ef2392983d0c46cc1dbdb0e17d27c209177e77` | Twisted26.10.0正式版/Stripe16.0.1/pyasn1 0.6.5を含む。main/AWSへ未反映 |

15:44 JSTのmetadata再確認ではRDS18.3/available・暗号化・非公開、readiness200/DB-cache ok。対象clusterの14:16 JST時点のサービス一覧はWeb1件で、常設worker/beatサービスは見つからない。別clusterや単発背景taskを今回網羅した結果ではない。共有DBの移行履歴を新しく取得したものでもない。

Web55の宣言はALLOWED_HOSTS=*、CSRF_TRUSTED_ORIGINS/PUBLIC_SITE_URLはhttps://stg.tableno.jp。Secretsを含む実効overlayは未取得。新しいHost制限imageを配備する際は、明示domainとimageをそろえた承認済み反映が必要である。

## 未統合の既知修正

| Draft PR | 固定head | 対象・状態 |
| --- | --- | --- |
| [46](https://github.com/sheepdog0820/iaia/pull/46) | a6f88882 | 移行準備/正式依存版/グループ2修正/明示OriginによるWS制限を統合。全12 CI成功。mainマージは既存の確認への回答待ち |
| [47](https://github.com/sheepdog0820/iaia/pull/47) | 8ff325c8 | readinessの例外本文を固定errorへ変更。全12 CI成功 |
| [48](https://github.com/sheepdog0820/iaia/pull/48) | 95d09609 | HTTP Hostと転送Hostの制限、内部HTTP health。全12 CI成功 |
| [49](https://github.com/sheepdog0820/iaia/pull/49) | d664bb40 | 共有cache検査キーによる誤503を解消。全12 CI成功 |
| [50](https://github.com/sheepdog0820/iaia/pull/50) | c4b5bdd0 | 限定証拠と未完了作業の文書整理。全12 CI成功 |
| [51](https://github.com/sheepdog0820/iaia/pull/51) | 8579bc5f | 画像変更の共通ロックと所有権再確認、同時主画像切替の500修正。全12 CI成功 |
| [52](https://github.com/sheepdog0820/iaia/pull/52) | 854c15c0 | 画像の保存先削除障害を日本語503へ変換し、参照/主画像設定を保持。全12 CI成功 |

順序は46→47→48→49→50→51→52。親のheadを変えず、親のmain統合後に子をmainへ付け替え、対象CI/tree/承認を再確認する。子PRをcodexの親へマージしない。今回の文書変更も別ブランチに置き、既存の検証headと既存承認対象を維持する。

854c15c0の[同一headのpushログ](https://github.com/sheepdog0820/iaia/actions/runs/41176512130)は全体2,417成功・129省略、PG690成功・361 subtests/省略0、Playwright243成功、system14成功。通常配布物内PG58件、Git由来570ファイル/entrypoint一致、実111 Python package監査0件/省略0。OSは52指摘（C2/H9/M6/L35）・未除外exit2で不合格。限定したnative調査を全native依存の適用除外へ広げない。

## 新しい隔離検証と限界

| 検査 | 実結果 | まだ証明していないこと |
| --- | --- | --- |
| DB・メディア復元 | PG18.3の別DBへ94表（非空23）・641行・90シーケンス、全11ファイル項目/参照/実ファイルが一致。APIClientの権限76件、欠落/破損/行/採番変更の検出4条件成功 | 多くの行は初期データ。実RDS/S3世代、実規模/同時writer、Unixファイルmetadata、実HTTP/TLS、RPO24h/RTO4h |
| 画像性能 | 100人・同時10フロー、各容量700要求、計1,400要求が期待結果に一致、予期しないエラー0。ZIP内JPEGは元bytesと一致 | 画像5枚境界/同一対象競合、長時間、実AWS/S3・ブラウザー、他の主要操作 |
| 背景メール | 実beat/Redis/worker/PG/SMTPの運用確認12項目成功。451後の期限どおりの自動再送、worker再起動、別2workerと実PGロックで1通、回復/古い通知取消、無効時保持/再有効化を確認 | 合成outboxを直接作成。実Stripe署名Webhook/権限の全フロー、実AWS/prefork容量、SMTP認証/TLS・受信箱、監視通知、SMTP受理直後のDB応答喪失 |
| コピー内移行（実AWS） | 承認されたd664/a85で4移行、技能6版190行/7版48行の比較、TLS/再接続READ ONLY、履歴/全体計画を確認。task exit0、後片付け完了。[実施結果](RDS_MIGRATION_REHEARSAL_RESULT_2026-10-31.md) | 課金/監査行は0。最新データの切替直前backup・共有適用・Web反映・DB/S3全体復旧・RPO/RTOは未実施 |

DB/メディア復元・画像性能・背景メールのローカル証拠はd664/a85によるもの。854/f77の画像API変更を含む性能測定は未実施である。

workerのSMTP到達は4回（拒否1/受理3）。受理は実受信箱への到達ではなく、SMTP受理とDB commit間の障害による重複可能性も残る。workerはsolo/concurrency1で、AWS予定構成のprefork/性能を再現していない。全試行の一時container/network・合成env/鍵は削除・不在を確認済み。

画像性能は4,553,465 bytes・2,048×3,072の同じJPEG、6版/7版各50人、100グループ・キャラクター/シナリオ/セッション各1,000、実Token認証の内部HTTPで測った。CPUとメモリを同時に変えた単発比較で、CPUだけが原因とは判定しない。Dockerのswap上限は記録したが使用量は未計測。HTTPS相当headerは実TLSではない。

| 操作 | 0.25 CPU/512 MiB p95秒 | 1 CPU/2 GiB p95秒 |
| --- | ---: | ---: |
| 画像追加 | 8.685 | 2.145 |
| 画像一覧 | 3.385 | 0.713 |
| 他者一覧拒否 | 3.406 | 0.800 |
| ZIP取得 | 7.374 | 2.056 |
| 他者ZIP拒否 | 3.799 | 0.841 |
| 削除 | 3.497 | 0.623 |
| 空一覧確認 | 2.997 | 0.769 |

0.25 CPU側は6操作が3秒基準に未達。1 CPU側は今回の7操作すべて3秒以内だが、全主要操作のQ02合格ではない。東京Linux/x86の[公開Price List](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-northeast-1/index.json)から、30日540時間を仮定した計算資源1 taskは約8.32→33.27 USD（+24.96）、720時間は約11.09→44.37 USD（+33.27）。税・他サービス・切替時のtask重複等は別で、実請求/費用上限ではない。容量・継続費用変更は未承認で、AWSを変更していない。

## 次の実行順・必要な判断

1. PR46の既存mainマージ確認への回答後、固定対象/CI/treeを再照合する。47〜52への承認拡張や無断マージをしない。
2. 承認済みd664/a85の非公開コピー内accounts0065〜0068リハーサルは完了。review SHA256 `844f0f13b3b012ee1dae7803e5e243f7657ca39c96e8b6f5057c5bccb607588a`を保持し、17手順記録/実変更SDK16件、専用資源の後片付けと元snapshot保持を確認した。予算案2 USD、実請求未確認。[結果](RDS_MIGRATION_REHEARSAL_RESULT_2026-10-31.md)は共有DB適用/Web反映の承認や実施を意味しない。
3. 切替直前に全writer、最新backup、元DB全体計画、image/Host設定、worker/beat/broker、IAM/Secret参照、容量/費用、復旧をそろえ、共有0065〜0068と配備の承認を確認する。最新元DB SQL計画は10月30日21:29 JST時点の4件未適用/不明0/重複1という履歴である。
4. F01〜F05の通常利用全フロー・ファイル保持/秘匿配送を確認する。F02所有権引継ぎは未実装で、人間の範囲判断を残す。ゲストclaimや管理者追加だけで完了にしない。
5. B01〜B05/I01〜I07の実Stripe/メール、OAuth初回/取消/失効/更新、Calendar/Sheets/Discord配送、ICS購読/CCFOLIA画像/ダイスを、承認された対象・宛先で確認する。
6. Q01〜Q04/O01〜O03の実機/全主要操作100人・同時10人・p95≤3秒・予期しないエラー0、OS/native指摘、常設処理/監視、DB/S3復旧とRPO24h/RTO4hを実証する。
7. O04の実情報保管/開示窓口、保存期間/背景透過保持、税務、DNS/ACM、費用上限/公開時期を確定し、全25条件の証拠と最終Go/No-Goを確認する。無料範囲・画像5枚共通・480円/月/4,800円/年・開示方式は決定済みとして維持する。

保持snapshotの実取得は10月30日08:12:13.770 JST。保管見直しは11月6日の同時刻以降で、移行未実施/未検証等で必要なら削除しない。切替直前backupやS3全体復旧の証拠として使わない。集計値とローカル証跡のhashは[機械判読の証拠一覧](RELEASE_CANDIDATE_EVIDENCE_2026-10-31.json)へ保存した。生のfixture・行データ・資格情報・実行承認記録はGitへ追加していない。

この変更は文書と集計JSONのみ。DB/schema、製品コード、設定、資源、Secrets、料金/保存方針、外部通知を変更しない。文書の復旧はrevertで、実環境のrollbackやDB逆移行は不要。文書headのCIはPRで別途確認し、854の成功を文書headの実行済みCIとは扱わない。

コピー移行の集計と証跡hashは[RDS実施証拠](RDS_MIGRATION_REHEARSAL_EVIDENCE_2026-10-31.json)を参照する。先行の集計JSONはd664のローカル検証記録として保持する。
