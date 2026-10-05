# 背景透過のジョブ作成時プレミアム権限再確認

## 対象・仕様

基準は `9f137533734c6c592d71d0025d3f4c1f5dda2272`、専用ブランチは `codex/background-premium-gate-20261006`。背景透過のみ有料という確定仕様を維持する。今回の追加修正は、アイコン `8567f49f` のmain・開発AWS反映承認や先行候補の承認へ追加しない。

認証時の `request.user.is_premium` だけでは、画像検証中またはuser行ロック待機中に失効が確定してもジョブを作成できた。ユーザー削除が確定すると `.get()` が500を起こした。初期の拒否は維持し、画像検証後に既存のuser行ロックを取得して、同じqueryで現在の `is_premium` を読む。行がない場合・権限がない場合は、上限計算・既存jobの期限処理・画像保存・job作成・ECS dispatchの前に403で拒否する。

初期拒否と再確認のエラーは「背景透過はプレミアムプランの機能です。」に統一する。既存のDRF `detail` 形式を維持し、6版・7版の既存clientが `detail` を表示する経路も静的確認した。staff/superuserを有料機能の新しい迂回条件にはしない。userとjobの既存ロック順は維持し、subscription行の追加ロック・Stripe照会は行わない。

認可の確定点は、user行ロック下のjob作成である。作成が先に許可されたjobを、後の権限失効で自動取消する変更は含めない。既存jobの所有者によるstatus取得・期限・画像保持の仕様を変えない。`is_premium` の同期遅延や購入・失効の実AWS運用が全面的に解決したとの主張ではない。

## TDD・検証

- 新規11件：通常9件と実PostgreSQLロック2件。古い認証flag、画像検証中の失効/削除、失効時の既存stale job不変、quotaより先の権限拒否、日本語初期拒否、staff/superuserの迂回防止、作成前の権限復帰、作成後の失効、行ロック待機後の失効/削除確定を確認する。
- SQLite RED初回：11件中7 failure・1 error・PG専用2 skip。テスト側の `error`/`detail` とpending statusの200/202という2つの期待値誤りを修正し、再REDは6 failure・1 error・2 skip。権限不足で202/429になるケースと、削除後の500を実装前に確認した。
- PostgreSQL RED：2件で1 failure・1 error。別接続が保持するuser行ロックを `pg_blocking_pids` で観測してからcommitし、最新失効を無視して202になるケースと、削除後の500を再現した。時間待ちだけで競合の成立と扱っていない。
- 最終Windows SQLite：関連143件中129成功・PG専用14省略、57.793秒、終了0。途中実行では2件のWindows media解放errorを検出し、[テスト後処理](IMAGE_API_FIXTURE_LIFECYCLE_2026-10-06.md)を修正した。初案のSQLite143件中129成功/14省略/60.161秒と、最終版を区別する。
- 最終隔離PostgreSQL：同じ143件すべて成功・省略0、62.481秒、終了0。変更POST関数47文/20分岐・新規テスト155文/2分岐は100%、除外0。画像APIの後処理を含む既存テストファイルも164文/4分岐100%（変更fixture関数18文/4分岐100%）。画像ビュー全体は文93%/分岐86%であり、モジュール全体100%とは報告しない。

関連範囲は `test_background_premium_gate`、`test_character_background_removal`、背景透過のfinalization/dispatch/uncertain/retention、`test_paid_feature_lifecycle`、`test_character_image_apis`、`test_character_multiple_images`。CIのproduction-database対象にも新規テストを追加する。DB/schema・worker・依存lock・Dockerfile・entrypointは変更しない。

Linux検証は既存イメージ `tableno:background-dispatch-runtime-3e5d46ee` （ID `sha256:395d5c051ed93596f47decd7e2ca6c7c8271d085228f9d6e6886ef0c7e1280f2`）に、今回sourceをread-only overlayして実行する。PG18.3はnetwork none・公開portなし・256MiB・512MiB tmpfs、アプリは同じnetwork namespace内だけで通信し、read-only rootと一時/tmp・mediaを使用する。S3/Redis/Checkout/課金メールは無効、資格情報は合成値のみ。共有DBや実ユーザーにアクセスしない。この結果は今回固定commitの通常配布イメージの検証ではない。

途中のLinux試験143件は全体media overrideがないためread-only保存先で20 error、media overrideを導入した初回harnessはDjango初期化順の `INSTALLED_APPS` errorとcoverage NoDataError、後処理初案の試験143件はPG接続closeによる2 errorだった。各ログを別名で残し、再実行で消去・成功扱いしない。PG起動直後の `pg_isready` は一度no response、その後acceptingを確認して試験を開始した。

## 証拠・未確認・復旧

ローカル証拠は `D:/tmp/codex-tableno-background-premium-gate-20261006/`。RED、途中の失敗、最終ログ、coverage JSON、隔離harnessを保持する。使い捨てPG container `a6f97ce41677463c5aa4ae15b8f6293816276ad41d7bf20a816ed1246dddb1e2` のID・用途label・network noneを照合し、test DBが破棄済みでbase/system DBだけであることを確認後、停止・削除した。アプリ検証containerも終了済みで、今回の常設container・公開portは残していない。tmpfs内の合成DBは消えており、必要ならfixtureから再作成する。

| 証拠ファイル | SHA-256 |
| --- | --- |
| `red-sqlite.log` | `ac96875b10e2ba0f9738c65e3b0f48c843345ad185541ccb8dc402ce240091aa` |
| `red-sqlite-corrected.log` | `4a2b2bcd05343d4491240f34d135e234a70d38bd788eb98255258437d9d9b65f` |
| `red-postgres.log` | `65c55deb7d1561f1ecc0d26f96de018fb548812d6a8117579edcdedbee29cd69` |
| `green-sqlite.log`（初回2 error） | `8f06e95948859a2d6f5c2ff4a125c6da895038b96a4e6672bc70e33f08670762` |
| `green-postgres.log`（初回20 error） | `fe6954cd59622ffc4d6baf58fcf69dd0530141b2858768423954fa3e15244f21` |
| `green-postgres-isolated.log`（harness error） | `6b6e3d2b79dd25b171aada84b2a69699a31a8037176f1cf1cfaa6ef4b4f79130` |
| `green-sqlite-isolated.log`（初案のみ成功） | `fb28c31037d7c14c2600a3ce805b57627e45748b221283798bf5bd6c140a7229` |
| `green-postgres-final.log`（初案2 error） | `897d6854666428c8fe3d8157830339d0f0a2499bafd08b050c4f9e409ccce2bf` |
| `green-sqlite-final.log` | `4a4ef09de3d9c8e46b20390bae86cee7f66bb0e500f7666215c6abdbee4cc95c` |
| `green-postgres-final-v2.log` | `f0d0fa0c495fd9a58bec3398ec79231a864cf41b08e89294ecbed9dbce891247` |
| `coverage.json` | `2001e78a1dd1d7a5adf1a6acdc79d9eb9000eb21fcbd6f015489fd06ba0efcc2` |

Black/isort/Flake8・Banditは変更Python3ファイルで終了0、Bandit指摘0。staged 7テキストのUTF-8/LF・BOM等の検査と差分checkが成功。文書テスト39件は0.035秒・終了0、変更3文書の相対リンク196件は欠落0、記載11証拠hashも一致した。ソース・日本語の自己レビューでは、権限再確認が副作用の前にあり、ロック順を増やさず、既存の作成許可済みjob/無料機能/保持期間を変えないことを確認した。追加修正を要する指摘は残っていない。

親9f137533の[CI run 37379808908](https://github.com/sheepdog0820/iaia/actions/runs/37379808908)は後続確認時点で5ジョブsuccess・Playwright実行中。今回候補のCI成功ではなく、実行中を理由にcancel/restartも行っていない。

今回の全体CI、通常配布物、実HTTP/ブラウザー、実ECS/S3/AWS競合、運用・性能・復旧は未確認。先行候補のCI/配布物結果を今回へ転用しない。OS/native指摘を解消・受容・抑制した変更でもなく、正式公開No-Goを維持する。

main/AWSはこの修正を反映しない。アイコン限定反映の再確認では、mainは8567f49f、開発AWSは定義54、CDNのアイコンは200。2026-10-06 07:06 JSTのサイトは既存夜間メンテナンス表示で503・desired/running/pending=0/0/0だった。ユーザーの依頼範囲を広げてservice起動・再デプロイは行っていない。

復旧はこの限定修正を作業ブランチ上で通常のrevertとして取り消す方法を用意する。新しいmigrationがなくDB逆移行は不要。force push・既存job/画像削除・元worktreeのハンドアウト作業変更は行わない。
