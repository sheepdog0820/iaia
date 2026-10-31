# 0068前の非公開バックアップと限定復元確認（2026-10-30）

ユーザーが承認した[バックアップ案](SKILL_BACKUP_PLAN_2026-10-29.md)を、通常起動後の08:10 JSTから実施した。08:34 JSTに復元検証と一時リソースの後片付けを確認した。共有DBへの移行・Web反映・正式公開は実施していない。正式公開は **No-Go** を維持する。

## 対象・固定した配布物

AWS account083773015316・ap-northeast-1、元DBは`tableno-aws-pre`。開始前にRDS available/PostgreSQL18.3・Web定義55のdesired/running1・pending0、readiness200/database-cache okを確認した。元DBの前倒し起動・既存サービスの更新・IAM/Secrets変更は行っていない。

probeは承認済みsource `873552d96be407cd3439a9f725be914f83802fbe`、ローカルimage `sha256:6c3afa3db45c184d66a486685a311970a23dcebd167f033565d8bbf337efc798` を使用した。新しいmainのマージ後も置き換えず、revision・probe2ファイルのハッシュと、送信後のmanifest/config digestを照合した。実行digestは `sha256:79eb3772b47faf1561562621deef1761d072d37a4cef88da6fc04fabb1f54826`。

## 保存したsnapshot

| 項目 | 確認結果 |
| --- | --- |
| ID | `tableno-aws-pre-pre0068-20261029-a` |
| ARN | `arn:aws:rds:ap-northeast-1:083773015316:snapshot:tableno-aws-pre-pre0068-20261029-a` |
| 実取得時刻 | 2026-10-30 08:12:13.770 JST |
| 状態・保護 | available、元DBと同じKMSによる暗号化、共有属性なし、専用タグ一致 |
| 保管見直し | 2026-11-06 08:12:13.770 JST以降。日付入りIDから期限を計算しない |

元snapshotは保持中。7日後でも移行未実施・未検証などで必要なら削除しない。自動失効や定期削除は設定していない。取得後の更新を含む将来の移行直前バックアップを、このsnapshotで代替しない。

## 限定した復元検証

別の専用RDS `tableno-restore-drill-0068-20261029-a`へ復元し、非公開・暗号化・同KMS・同VPCと、専用SG2件の通信範囲を確認した。元DBの接続先をアプリへ差し替えず、アプリ/workerも起動していない。

単発task `95bd33fee10b40bf9c770c9716ab8f03` は専用定義`tableno-restore-drill-0068-probe-20261029-a:1`を使用し、exitCode0で停止した。RunTask要求から停止まで70.55秒。task/containerの実image digestも上記の固定値と一致した。既存execution roleからDB_PASSWORDだけを注入し、task roleとECS Execは付与していない。

最小Django設定のprobeが期待した別ホスト/DB名・TLS・PostgreSQL18を確認し、DBで強制したREAD ONLYトランザクションで履歴・物理列/制約・技能の旧内訳集計を取得した。format_version2/read_only=true/server_major18をログと照合した。検証ログと集計記録には、個人の行データや認証情報を出力・保存していない。

取得時点の復元DBでは、accountsの最終履歴は`0064_preserve_character_descendants`だった。次の4件は未適用である。

| 移行 | 内容 |
| --- | --- |
| 0065 | Stripe作成要求・冪等性の記録テーブル |
| 0066 | Stripe請求状態テーブル |
| 0067 | 課金メール配送テーブル |
| 0068 | 技能のbonus_pointsをother_pointsへ合算 |

0068の適用記録はなく、6版には旧bonus_pointsが非ゼロの行が存在した。両版とも合算時のint32範囲超過は0件。旧内訳を含むsnapshotから読み取りが成立したことを確認した。これは取得時点の復元先の証拠で、現在の元DB全体の移行計画・他アプリの全履歴・全テーブル/全行一致を証明しない。

このため「未適用は0068だけ」とする既存の検証付きコマンドを、そのまま共有DBへ実行できるとは扱わない。0065〜0068の範囲・現在の他アプリの未適用分を確認し、隔離検証と新しい承認対象を準備する。

## 後片付けと費用

停止済みprobeの所有と状態を確認し、専用task definitionをINACTIVEにした。専用RDSは最終snapshotなし・自動バックアップ削除付きで削除し、専用ENI解放後にSG相互参照を解除して2件とも削除した。専用ECRタグとmanifestも不存在を確認した。RunTaskやsnapshot作成の再実行は行っていない。

DB削除後に自動snapshotがしばらく一覧へ残ったため、削除要求の`DeleteAutomatedBackups=true`をCloudTrailで照合し、同じresource IDを観測した。自動バックアップセット・自動snapshotの双方がなくなるまで待ち、別の削除APIを追加せずに後片付けを確認した。復元要求から最終確認まで17.73分で、DB2時間/probe15分の運用目標内だった。

08:34 JSTの確認では、一時RDS・その自動バックアップ/snapshot・専用SG/ENI・専用ECRタグ/manifestの残存は0。停止済みタスク履歴とINACTIVE task definitionのメタデータは残る。元RDS available、Web定義55/readiness200/database-cache okを再確認した。単発予約`rds`は完了後に削除した。

承認予算案は2 USDで、実請求の強制上限ではない。実請求額は未確認であり、snapshot保管の費用は継続する。[当初の見積もり](SKILL_BACKUP_PLAN_2026-10-29.md)を実績請求と表示しない。

## 次に必要な作業

共有0065〜0068の適用は別承認対象。実行前には、最新の元DB履歴/計画、全書き込み経路の停止、適用直前の新snapshot、検証済みの固定配布物と復旧方法を提示する。0068の逆移行は旧内訳を復元しない。DB/S3全体の復旧・切替とRPO24h/RTO4h、実課金/外部連携・性能・セキュリティ・公開判断の[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は未完了である。
