# 背景透過の診断機能の初期化防止（2026-10-28）

main 945441ffを基点に、既知c7390ee3からDocker設定・サービス・回帰テストの4ファイルだけを分離する。PR #20は承認後21:37 JSTに通常マージ済みで、承認head714c2ed0とtree一致を確認した。共有AWS・DB・実Stripeは変更していない。

## 再現と修正

固定依存のONNX Runtime 1.29.0は、[公式実装](https://github.com/microsoft/onnxruntime/blob/2e2543fbe9fae542f921d47a72d21d5a4ef0b710/onnxruntime/core/platform/telemetry_environment.h)でPOSIX初期化前の環境設定を参照する。Windowsは別のAPI制御であり、Dockerの環境設定だけを全環境の保証としない。

mainと同じ製品treeの通常イメージ0739d9e4を、network none・fresh tmpfs home・UID10001で起動し、importだけで`deviceid`と`onnxruntime.db`（WAL/SHM含む）が作成されることを再現した。CI用抑制変数は指定していない。内容は読まずファイル名だけを確認した。自己申告build infoは公式commitの短縮2e2543fbe9と一致するが、署名されたビルド来歴の証明にはしない。送信はネットワークで遮断したため、実環境の送信有無・内容は未確認である。

Dockerに`ORT_DISABLE_TELEMETRY=1`を設定し、サービスでもnative import前に値を設定する。native APIによる無効化後にrembg・U2NET/CPUを読み込む。既にnativeが読み込まれている場合も毎回APIを呼び、無効化が失敗した場合はモデル処理を始めず既存の失敗経路へ戻す。先行import時に作成済みのファイルを削除する修正ではない。背景透過の有料制限・モデル・画像上限は維持する。

## 検証

- 製品変更前は10失敗・27成功（subtest失敗を含む）。修正後はモデル/起動設定/背景透過API/構成/公開条件の5ファイルで99テスト・21 subtests成功、省略なし。
- サービス8実行文を全て実行し、当該モジュール100%。全アプリ100%とはしない。import順序、未設定や偽の環境値、複数回呼び出し、無効化API失敗時の処理中断を検証した。
- Black/isort/Flake8/Bandit・差分検査成功。自己レビューで追加の対処事項なし。新しい利用者向け文言はない。DBは隔離SQLiteだけを使用し、ECS/S3は既存mockを使った。初回の関連検査指定に存在しないファイル名がありcollection前に停止したため、実在する対象を指定した再実行の99件だけを成功記録とする。
- 製品修正d5941a0aのgit archiveから通常イメージ`sha256:b296ae978dafe1c2de417aa0f7f033cb4f288324912a8e915849bbe38bb076fd`を構築した。11製品/テスト/依存ファイルと実entrypointがGit blobに一致し、ビルド定義のarchive実バイトとGitの命令も一致した。UID10001・read-only・権限を落とした配布物内で隔離PostgreSQLの31テスト成功、省略なし。pip/pytestや製品ソースoverlayは追加していない。Dockerfileのstage/Git blobはUTF-8/LFである。
- 同配布物で、既存のU2NETモデル（175,997,641 bytes、SHA256 `8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491`）を単一ファイルreadonly mountし、合成128×128画像の実推論を2回確認した。Docker既定値と`0`上書きの両方で環境値が`1`となり、RGBA PNG・alpha 0〜255・同一結果hash `97118d98655762cab2a06137caeeba448a79f62b8cb7eacbd42f7b066c356cde`、診断ファイル0件。各回fresh tmpfs home・network noneで、新規ダウンロードや実ユーザー画像は使っていない。実portraitの品質やAWS性能の証拠にはしない。
- [Draft PR #22](https://github.com/sheepdog0820/iaia/pull/22)の最終CIは未完了。古い候補の成功を今回の証拠に置き換えない。

## 境界と残作業

実ユーザー画像・保存済み診断情報、AWS、共有DB、Secrets/IAM/OAuth、料金・費用、外部通知は変更しない。マイグレーション追加・依存更新もない。main追加マージは今回のheadと結果を示して別途承認を確認する。復旧はrevert PRだが診断初期化の防止も戻るため、無効化を保つ修正版を優先する。

背景ジョブの完了・配送・保存期間処理の競合は別の修正候補で、今回の完了に含めない。実AWSの推論品質・負荷、Windows実行、既存診断情報の扱い、OS50指摘・Twisted RC2と[正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は未完了/No-Goを維持する。
