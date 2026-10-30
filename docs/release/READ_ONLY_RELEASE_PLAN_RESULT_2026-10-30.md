# 共有開発RDSの全体移行計画・読み取り検査結果（2026-10-30）

ユーザーが「読み取り専用AWS検査と予算案1 USDを承認」と回答した対象を実行し、21:30 JSTに検査成功と後片付けを確認した。適用履歴がある12アプリを含む全体計画の未適用分は、accounts0065→0066→0067→0068の4件だけだった。共有DBへの適用・履歴修復・業務データの行取得・Web反映は行っていない。正式公開は **No-Go** を維持する。

## 対象と実行結果

| 項目 | 確認結果 |
| --- | --- |
| AWS | account083773015316、ap-northeast-1、profile tableno-pre |
| 元DB | `tableno-aws-pre`、PostgreSQL18.3、private/encrypted、available |
| Web | 定義55、desired/running1・pending0、既存digest `6d4050ec19ba5d34740643d515436baa5dd27b99a912b9c20ad7a9af0812af06` |
| 検査のsource | `297a217da2d3445697c56171da212524d9433537`、PR #38の固定候補。mainへマージしたものとして扱わない |
| local image | `sha256:0fe931f78d4280275d151381601589bf36d7edf4c0fe81171d2e7cade2b93e15` |
| AWSで実行したdigest | `sha256:7e111c9577dd594d36d93de2b8a6644970ece259f190900b4311763ba0286187`。ECR応答manifest/configとlocal imageを照合 |
| 承認入力のSHA256 | `5ddc50825dc68de6b6d2a085293e1eb8666bba9375141e22e027a2cc00eb4294` |
| probeのSHA256 | `1e705c54f73333671c0f7929d6f33a10bf7c634d34e14b571a62789e78b4fef6` |
| 専用定義 | `tableno-readonly-release-plan-20261030-a:1` |
| 単発task | `c041c6996e1542db861f3de848cc7f90` |
| 結果 | exitCode0、read_only=true、tls=true、server_major18 |
| RunTask要求から停止 | 67.126秒。15分の運用目標内 |

起動前に元RDS・Web・接続先host/DB/user/port・既存DB_PASSWORDの参照・execution role・subnet/SG・readiness200/database-cache okを承認時の値と照合した。既存サービスの更新や元DBの起動操作は行っていない。

専用taskは0.25 vCPU/512 MiB、UID10001、root filesystem read-only、capabilities全削除で、pythonの固定inline codeを直接実行した。アプリserver/worker・通常entrypoint・移行コマンドは起動していない。task roleとECS Execはなく、既存execution roleからDB_PASSWORDだけを注入した。実OAuth/Stripe/メール等の資格情報は渡していない。

接続開始時からPostgreSQLのdefault_transaction_read_onlyをonにし、Djangoアプリ登録前の書き込みも拒否する構成。REPEATABLE READ/READ ONLYトランザクションで、django_migrationsのapp/name・整合した履歴・全leafへのMigrationExecutor計画を取得した。期待host/DB名、PostgreSQL18、TLS接続も確認した。TLSはsslmode=requireによる暗号化で、verify-fullによるCA検証ではない。

## 検証した全体計画

適用済みのapp/nameは重複を除いて169件、重複行は1件、不明な適用履歴は0件だった。今回のreportは重複の総数だけを出すため、重複行の名前・由来を再特定したとは扱わない。朝のsnapshot検査で重複を認識していたことを理由に、履歴を変更・削除していない。

| 未適用の順序 | migration | 内容 |
| --- | --- | --- |
| 1 | accounts.0065_stripe_billing_requests | Stripe作成要求・冪等性の記録 |
| 2 | accounts.0066_stripe_invoice_states | 請求状態 |
| 3 | accounts.0067_billing_email_delivery | 課金メール配送 |
| 4 | accounts.0068_merge_skill_bonus_into_other | 技能の旧bonus_pointsをother_pointsへ合算 |

4件とも順方向で、他アプリの未適用分はなかった。これは21:29 JST時点の固定sourceに対する元DBの計画であり、全物理スキーマ/業務行の一致、以後の別操作、適用成功・復旧成功を証明しない。実際の適用直前にも計画と稼働版を照合する必要がある。

## 後片付けと運用上の記録

- 同じtask ARNを継続して観測し、exit0と停止を確認した。既に停止していたのでStopTaskの変更APIは呼ばなかった。
- 応答で所有と内容を確認した専用定義を登録解除し、INACTIVEを読み戻した。専用ECR tag `readonly-plan-297a217d-20261030-a`とdigestの不在、応答ENIの解放を確認した。他のtagのimageを削除していない。
- 既存CloudWatch groupには検証済みの移行メタデータを記録し、既存の3日保管を変更していない。秘密値・業務データの行は出力・保存していない。停止済みtaskの履歴とINACTIVE定義のメタデータは残る。
- 登録直後の照合は、AWSが追加した空のcapabilities.addとenvironmentの並び順で停止した。空の追加権限と同一のname/value集合だけを同値として扱うよう読取検証を修正し、登録済みの同じ定義を確認した。別の定義・taskを作り直さず、追加権限・値の変化・重複environmentは引き続き拒否する。ガード7試験も成功した。
- 21:30 JSTの最終確認で元RDSはavailable、Webは定義55のdesired/running1、readiness200/database-cache okだった。共有DB適用・Web反映・IAM/Secrets変更は行っていない。

1 USDは今回の単発検査の承認予算案で、実請求額は未確認、請求の強制上限ではない。朝に取得して保持中のsnapshotは今回の変更対象ではなく、将来の移行直前backupを代替するものではない。

## 次の段階と承認範囲

元DBの全体計画が4件だけであることの確認は完了した。PR #38のmainマージ、全writerの停止・新しい直前backup・実データcopyでのリハーサル、共有4件の適用、新Web/背景処理・IAM/容量・費用の変更は、それぞれ必要な準備・検証・人間の承認が残る。今回の承認をこれらへ拡張しない。

[最新のOS再監査](RUNTIME_OS_HIGH_CRITICAL_SCOPE_2026-10-30.md)は52指摘・exit2で、gcc-14のpriority queue由来High等が未解決である。aligned newは固定OS libraryの実binaryと30ケースを照合して適用範囲を判定したが、正式公開条件の完了にはしない。実課金/外部連携・性能・DB/S3全体復旧・運用と[正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)も維持する。

読み取り検査なのでDBの逆移行は復旧方法にしない。検証済みレポートは`tmp/readonly-release-plan-verified-report-20261030.json`、実行応答は`tmp/readonly-release-plan-execution-20261030.json`、後片付けは`tmp/readonly-release-plan-final-result-20261030.json`に保持している。これらのprivate artifactをGitへ含めず、本変更は調査結果の文書化だけとする。
