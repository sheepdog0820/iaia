# Google共有実行権: PostgreSQL保存SQLの前後での障害

## 対象と検証の限界

2026-10-08。基準は `b348b06af5328bdc86e6305f3c6facb38de26556`、作業ブランチは `codex/google-db-boundary-20261008`。[通常配布物の強制停止検証](GOOGLE_SHARED_RUNTIME_2026-10-08.md)に続き、[設計T10](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)のDB保存失敗による偽解除を検査する。

追加は `schedules/test_google_target_execution.py` のPostgreSQL専用回帰試験と記録だけ。製品コード・schema・依存・認可・利用者向け文言は変更しない。既存のreceipt保存失敗試験はORMから模擬DatabaseErrorを起こしていた。今回は実PostgreSQLがSQLSTATE `22012`を返し、実際のatomic transactionがabort/rollbackすることを確認する。機能追加や不具合修正の完了ではなく、既存実装の受入証拠を補う単位である。

通常イメージ `sha256:9be20cc3a4ac1bee2974f2e150a2ecc26689ebfabcad22bc1a70608c2bb1ab3b` のentrypointを使用するが、検査ソースをread-only `/workspace`へmountしている。**新しい通常配布物の検証ではない。** Google通信とaccess-token取得はfixtureでmockし、未mock Requestsは拒否する。ログの `http=` はmock送信関数の呼出数であり、実HTTP到達や実Google適用を示さない。Celery task本体は呼ぶが独立worker/broker配送ではない。

PG18.3は固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、専用network none・read-only・512 MiB/2 CPU・tmpfs、ホストportと永続volumeなし。検査processはPGのnetwork namespace内のlocalhostだけへ接続し、2 GiB/2 CPU・非root/read-only。developer env/Secrets/S3/メール・起動時migration/collectstaticは無効。合成fixture DBと専用test DB以外を使わず、全20ケースは新しい所有session/Sheet対象で分離し、実commitをrollback savepointで隠さない。

## 保存境界20ケース

実APIでjob/admission/outboxを受付後、実worker関数を呼ぶ。Djangoのexecute wrapperは対象SQLを一度だけ選び、その**実行前または実行後**に同じconnectionで `SELECT 1 / 0` を発行する。SQL後ケースでは元INSERT/UPDATEを実際に実行してからDB側でtransactionを失敗させる。ORM save/updateはmockせず、原本例外のSQLSTATE、注入が一度であること、元SQLの実行有無をassertする。

| 境界 | 障害後のrequest | 初回mock書き込み | 不変条件 |
| --- | --- | --- | --- |
| INTENT INSERT | 行なし | 0 | 送信前の実行権を勝手に解除しない |
| receipt UPDATE | INTENT、statusなし | 1 | 応答を受けても保存失敗ならKNOWNに変えない |
| job SUCCEEDED UPDATE | KNOWN / 200 | 1 | sourceの成功を部分commitせずRUNNINGを保持 |
| journal FINISHED UPDATE | KNOWN / 200 | 1 | closed_atを部分commitせず未解決記録を保持 |
| target holder解除 UPDATE | KNOWN / 200 | 1 | Calendarの複数対象も含めてholderを部分解除しない |

各境界の前/後 × Calendar/Sheets = 20ケース。例外後のfinallyはUNKNOWNを確定し、closed_atはnull、全allocationのtarget tokenは元executionと一致した。実行期限は未来のまま、時刻・期限注入なし。元jobの再配送は状態保持/inactive-job・mock送信0、同じ対象の新しいAPI jobはtarget-waiting・未開始・cipher保持・mock送信0だった。元実行journalは一つだけで、新しいholderを作って回避していない。

INTENT境界の4ケースは初回送信0、残る16ケースは各1回。これはmockの呼出数であり、外部適用の証拠やexactly-once保証ではない。finallyが動かないSIGKILL時のACTIVE保持は先行記録にあり、今回のUNKNOWN確定と混同しない。DB再起動、接続切断、commit応答喪失、物理ストレージ障害、実Googleは今回の範囲外。

## 回帰・品質・記録

専用PGの最初の局所実行は1テスト内20 subcase成功、9.819秒、container終了0。追加60実行文・16分岐先は100%、変更行除外0。coverageは生存中processからexportし、tmpfs停止後の取り出しや未測定の行を合格扱いしない。coverage JSONの空キーをPowerShell objectへ変換する診断は不成立だったため、元JSONを保持し `-AsHashtable`で解析した。ケース本体の失敗ではない。

広域回帰はGoogle/async job/PG credential等379件成功・省略0、400.241秒、container終了0。追加20ケースをこの集合内でも再実行した。source mount/coverage計測付きの実行であり、先行の通常配布物378件とは分ける。変更60文16分岐先100%・除外0、実行前後の変更source SHA-256一致を確認した。文書/CI69件も成功。Black/isort/Flake8/Banditは変更したPython1ファイルで終了0。

自己レビューではSQL選択が一度だけであること、前/後の実行有無・原本SQLSTATE・未来期限・rollback後のjob/request/journal/全targetをassertすること、元の再配送拒否と後続待機のassertionを緩めていないことを確認した。APIで受け付けたIDを使用し、同時刻の別jobを選ばない。利用者向け文言・認可・model・migrationを変えず、追加の修正を要する指摘は残らなかった。元checkoutのハンドアウト関連13項目は別作業として保持する。新しい画面変更がないため、この単位で追加ブラウザー合格を主張しない。

23:11:39 JSTに完全ID/name/label/image/network/read-only/mount/終了状態を照合し、所有3 container/tmpfsを撤去した。test DB/他fixture connection0・PG停止0/OOM false・残所有container0。測定中processを削除していない。合成データは消えたが、source・image・log・coverage・再作成用scriptは保持した。共有環境や元checkoutの変更は触っていない。

証拠は `D:/tmp/codex-google-db-boundary-20261008` のscript、固定完全container ID/inspection、初回/広域log、coverage JSON、case/差分coverage照合、cleanupとSHA-256 manifestへ保存する。先行単位 `b348b06a` はcommit・通常push済みで、733選定source/assetsと検証imageの一致を保存した。[CI37788447885](https://github.com/sheepdog0820/iaia/actions/runs/37788447885)は対象head一致で追跡し、今回のテスト追加commitのCIとは区別する。

GitHub open Issueは別UIの#1のみ。本課題の新規Issueは先行403/CLI未認証のままなので、[下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)へ結果を追記し、Issue全体を閉じない。

## 残条件・影響・復旧

正式公開は**No-Go**。T10全体、T01〜T15全体、DB再起動/保存・実行期限、owner/session/sync全削除・再連携、全lock順、共有Sheetの認可/資源上限、legacy停止/drain/移行、privacy/保持方針、日本語待機UI、結果照合と限定回復は未完了。実Google/OAuth公開審査、常設基盤、Stripe/AWS購入・実メール、実AWS性能、RDS+S3復旧、事業/税務/運用条件も残る。

先行の新規OS scanは37指摘（HIGH 1 / MEDIUM 1 / LOW 35）・終了2で未合格。今回は依存やbase imageを変更せず、新scan/解消を主張しない。

main/ECR/ECS/S3/CloudFront/共有DB/実データ/Secrets/IAM/実課金/外部通知/容量・継続費用は変更しない。favicon承認を拡張しない。未配備なので実環境切戻しは不要で、今回のテスト/記録は通常revertで取り消せる。共有反映時には対象SHA・稼働版・drain/保持/送信停止・具体的復旧手順と必要承認を揃える。journalをDROPして旧workerを再開する方法は復旧案にしない。
