# 移行準備・調査記録・Twisted正式版の統合候補（2026-10-30）

main deddd772を基点に、次の固定した候補を専用codexブランチでまとめた。[PR #41](https://github.com/sheepdog0820/iaia/pull/41)の固定headは`a78d15bf20cf4ac0fe6e050e72484fb7ef69fb4e`、13ファイル。2026年10月31日時点で統合後の通常配布物・CIの検証が完了し、mainマージの承認待ちである。個別の候補のheadは変更せず、既存のPR #38の承認依頼をこの追加範囲へ拡張しない。正式公開は **No-Go**。本統合は共有DBへの移行・Web反映・公開を実行するものではない。この文書の後続更新も、PR #41の固定headを変更しない。

| 対象 | 固定head | 個別の証拠 |
| --- | --- | --- |
| PR #38：課金の前提移行と技能合算の検証付き適用準備 | `297a217da2d3445697c56171da212524d9433537` | PG33件/38 subtests、全99実行文/44分岐、通常配布物54件、CI12成功。共有適用なし |
| PR #39：最新の共有DB/OS調査 | `1a8029e82ed0c00bc09b666514cd4afde1850a88` | 文書2件。CI12成功（全体2379/105省略、PG588/223 subtests、UI243）。元DBの全体READ ONLY計画は4件だけで、不明履歴0。専用AWS資源は後片付け済み |
| PR #40：Twisted26.10.0正式版 | `d3e5565b8de3b001e983c53ec2a0e7a9e516c4f8` | 3ロック/実111 packageの監査0、個別PG86件/28 subtests、通常配布物のHTTP/WebSocket/Redis成功。最終CI12成功（全体2379/105省略、PG588/223 subtests、UI243） |

4件の明示オプションのコード/テストは#38、依存入力/3ロックは#40と同一の内容を採用する。移行ファイル・料金/権限仕様・Stripe API・製品UIの追加変更はない。課金の冪等性/配送テーブル3件と技能合算は、将来の承認済み適用に備えるもので、通常のWeb起動に移行を混ぜない。

進捗表と移行準備文書は、21:29の元DBの全体計画と52件の最新OS監査を参照するよう更新する。F/B/I/Q/Oの25受け入れ条件を削除・緩和せず、個別の成功と統合後の検証を区別する。25項目の基準文がmainと一致することを機械照合し、6つのコード/依存ファイルが上記の固定headとbyte単位で一致することも確認した。

## 統合後の検証

隔離PostgreSQL18.3/Python3.11.18/Django5.2.17と正式版Twisted26.10.0で、関連140件・85 subtests成功、省略0。4件モードと既定の0068限定、事前検査、起動/HTTP診断保護、Sentry情報保護、本番設定、systemテストを組み合わせた。コマンド全99実行文/44分岐を通過し、未通過0。11警告は既存のDjango6非推奨制約と日付fixtureのnaive datetimeであり、成功件数から除外せず記録した。

変更したPython2ファイルのBlack/isort/Flake8と製品コマンドのBandit成功。全差分をレビューし、接続先固定、余分な計画/未知履歴拒否、技能と課金の全物理列比較、DDL/データ/履歴rollback、COMMIT応答喪失時の読み取り再確認と自動再適用禁止、日本語の利用者向け文言を確認した。統合に起因する追加の修正指摘はない。

通常imageは`sha256:7d5dfc5a87b25d17cf0843864e35baeb1d95e7066bb4cb5dec5099f5e807018d`、sourceは上記a78d15bf。Gitの560ファイルとentrypointを照合し、製品sourceの上書きや追加pip/pytestなしの配布物内で関連PG54件が成功した。HTTP readiness200/database-cache ok、匿名WebSocket403、認証済みRedis/msgpack往復、他利用者への非漏えい、disconnect時の後片付けを確認した。実インストール111 packageのPython依存監査は既知0件。これらは隔離環境での結果であり、AWSへの配備成功ではない。

[最終headのCI全12チェック](https://github.com/sheepdog0820/iaia/actions/runs/41062625803)は成功。全体2,379成功・123省略、PostgreSQL606成功・239 subtests（省略0）、Playwright243成功を同headのpush実行ログで確認し、PRへ記録した。全体テストの省略をPostgreSQLの省略なしと混同しない。

## 共有環境の状態と残作業

21:29 JSTの元DBは、適用履歴がある12アプリを含む全体計画でaccounts0065→0066→0067→0068の4件だけが未適用だった。不明履歴0、重複総数1。21:30の後片付け確認では元RDS available・Web定義55/readiness200。朝のsnapshotは保持中で、11月6日08:12 JST以降に必要性を見直す。後続の更新を含む移行直前backupとして代用しない。

保持中snapshotから専用非公開RDSへ復元し、コピー内だけで4件を適用するリハーサルは準備済み・別の承認待ちで、AWS未実行である。8件の合成TLS/PG試験・36境界試験・17 SDK入力schema検査は成功したが、実AWSの復元コピーでの移行成功ではない。source/DBの適用直前再照合、全writerの停止・時間帯、直前snapshot、共有4件の適用、新しいWeb/背景処理・限定IAM/設定ポインター・容量/費用は準備と個別承認が残る。DBの自動逆移行、COMMIT応答喪失時の自動再適用、更新を捨てるsnapshot復旧は行わない。

同じ統合imageのScout1.29.0監査もOS52指摘（C2/H9/M6/L35）・exit2で、未除外のまま保持する。[MySQLdb](MYSQL_NATIVE_PBDS_BUILD_SCOPE_2026-10-30.md)と[ONNX Runtime](ONNXRUNTIME_NATIVE_SOURCE_SCOPE_2026-10-31.md)の後続調査を、配布物全体のPBDS由来HIGHの解消判定へ拡張しない。Twistedの正式版はこの統合候補へ入るが、main/稼働AWSは未反映である。実Stripe・OAuth/外部配送・性能・DB/S3全体復旧・事業者運用など、[正式公開の全条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

mainマージは統合後のhead・実行結果・影響・未確認事項を示して承認依頼済みで、回答待ちである。既存の承認依頼を繰り返さず、承認対象にAWS操作・共有DB変更・実Stripe・外部通知・正式公開を含めない。復旧はrevert PRで、4件モードがなくなり、TwistedはRC2へ戻る。既にmainにあるPR #37等の修正を保持し、DBの逆移行にはしない。
