# 背景透過native runtimeのtelemetry初期化防止（2026-10-05）

## 結論と範囲

背景透過で使うONNX Runtime 1.29.0のPOSIX初期化が、明示的なopt-outなしでは永続識別子とtelemetry用SQLite DBを作成することを、既存の通常配布物で再現した。Docker起動時の環境設定と背景透過サービスのimport順序・native APIによる無効化を追加した。U2NET/CPU・プレミアム権限・画像上限は変更していない。

修正後の通常Dockerイメージで、既存モデルを使う実推論2ケースが成功し、透過PNG生成とtelemetryファイル未作成を確認した。外部送信は全ケースでDockerのネットワーク遮断により禁止したため、過去や稼働AWSで送信されたかは未確認。画像が送信されたという証拠も得ていない。

main/AWS/ECR・共有DB・Secrets/権限・課金・容量・メールは変更していない。今回修正の全CIはpush後に確認する。完了済みfavicon承認と固定6b6c570cの反映案には追加しない。正式公開はNo-Goを維持する。

## 一次情報と再現

- [公式v1.29.0 release](https://github.com/microsoft/onnxruntime/releases/tag/v1.29.0)のソースcommitは `2e2543fbe9fae542f921d47a72d21d5a4ef0b710`。実配布binaryのbuild infoも短縮commit `2e2543fbe9` を返した。ただし自己申告build infoであり、署名付き完全ビルド閉包の証明ではない。
- [固定commitの環境設定](https://github.com/microsoft/onnxruntime/blob/2e2543fbe9fae542f921d47a72d21d5a4ef0b710/onnxruntime/core/platform/telemetry_environment.h)は `ORT_DISABLE_TELEMETRY` をPOSIX初期化時に参照する。CI/単体試験の環境変数も初期化を抑制するため、CIだけでは通常実行の証拠にならない。Windows ETWは同じ環境変数を参照しない。
- [固定commitのPOSIX実装](https://github.com/microsoft/onnxruntime/blob/2e2543fbe9fae542f921d47a72d21d5a4ef0b710/onnxruntime/core/platform/posix/telemetry.cc)は、opt-out時にuploader/永続化の初期化前に終了する。import後のAPI呼出しだけでは先行初期化を取り消せない。
- [識別子保存の実装](https://github.com/microsoft/onnxruntime/blob/2e2543fbe9fae542f921d47a72d21d5a4ef0b710/onnxruntime/core/platform/posix/device_id.cc)と、隔離した通常6828f209イメージのimportのみの試験で、fresh home内に `deviceid`、`onnxruntime.db`、同WAL/SHMを確認した。識別子の中身は読んでいない。import前のopt-outとAPI無効化を指定した比較ケースではhomeファイル0件。

## 実装・TDD・レビュー

- `Dockerfile`：全runtimeコマンド/workerのnative import前に `ENV ORT_DISABLE_TELEMETRY=1` を設定。
- `accounts/background_removal.py`：環境値が未設定/偽でも `1` を設定し、ONNX import→`disable_telemetry_events()`→rembg import→明示U2NET/CPU sessionの順序を固定。Windows/読み込み済みモジュールにもAPIを呼ぶ。無効化APIが失敗した場合はモデル読込前に例外とし、黙って処理を続けない。
- 新規5テストメソッド（うち6環境値のsubtest）を先行追加し、REDで失敗を確認してから実装。import順序、各環境値、複数リクエスト、API失敗時のfail-closed、Docker設定を検証。既存2モデルテストを保持。
- 最終関連99件成功、16.533秒、省略なし。対象はmodel/Docker entrypoint/背景透過API/infrastructure/release documentation。使い捨てSQLiteテストDBのみで、外部ECS/S3/モデル例外は既存の隔離mock試験。
- coverage：サービス8実行文、modelテスト74実行文/6分岐すべて実行、双方100%。これは当該ファイルの範囲で、全アプリ100%ではない。
- Python 3.11.1で変更Python3ファイルのBlack/isort/Flake8成功、Bandit指摘0/エラー0。権限、料金、DB、外部通信、異常時挙動と実diffを自己レビューし、要修正指摘なし。新しい利用者向け文言/UI変更なし。文書追加後の39テスト成功、証拠8hash一致、文書2件の相対リンク188件欠落0。stage検査5テキストとDockerfile別確認でUTF-8/LF・BOM/置換文字なし、空白差分検査成功。DockerfileのWindows作業コピーの改行とstage内LFは区別した。

このサービスより先に他の呼出し元がnative runtimeを読み込み、初期化した保存ファイルは取り消せない。Docker既定値はその先行importも防ぐが、既存実環境の履歴消去や他ライブラリー全体の通信停止を保証する変更ではない。

## 通常配布物と実モデル

基点 `be82fc205b0252a47a74593d4ce23b0a7caf95cf` に今回4ソースファイルをstageしたGit tree `2279b486770c49d0b5ffdce744f31fc48a1008ff` をarchiveし、通常Dockerfileでbuildした。文書追加前のtreeなのでコミットSHAの配布物とは区別する。ソースoverlay/SDK差替えなし。675選定ファイル同一、欠落・不一致0、Pythonキャッシュ0。今回4ファイルもcheckoutとbyte一致。

- tag：`tableno:background-telemetry-20261005`
- image ID：`sha256:dffd9770bef02d0865b7ce50f43b2679fa2eb8992404c41a768997431d66e156`
- label：`org.tableno.source-tree=2279b486770c49d0b5ffdce744f31fc48a1008ff`
- model：既存 `u2net.onnx` 175,997,641 bytesを単一ファイルreadonly mount。SHA256 `8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491`。新規ダウンロード/モデル変更なし。

各ケースはfresh home/tmp、`--network none`、2 GiB/1 CPU、通常非rootユーザーで実行。CI/単体試験抑制環境変数なし。入力は合成128×128白背景/赤矩形で、実ユーザー画像ではない。

| ケース | 呼出し前→後の環境値 | 結果 | telemetryファイル |
|---|---|---|---|
| Docker既定値 | 1→1 | PNG/RGBA、128×128、alpha 0〜255 | 0 |
| operatorによる0上書き | 0→1 | 同上、同一結果hash | 0 |

出力SHA256は双方 `97118d98655762cab2a06137caeeba448a79f62b8cb7eacbd42f7b066c356cde`。これは透過処理が動くことの限定確認で、実portraitの品質・AWS負荷/性能・常設worker・本番モデル取得の成功ではない。使い捨てcontainerは終了時削除、model mountはreadonly。

## 残条件・復旧

今回イメージのWeb通常起動/全API/PG/全OS監査は再実施していない。先行6828f209の609 PG/27 HTTP成功や全OS39指摘（HIGH3/MEDIUM1/LOW35、Python0）を今回の検証結果へ転用しない。依存/OS更新は行っておらず、PBDS/LLVM/ONNXのnativeビルド閉包・CVE解消は依然未証明。[先行配布物記録](STRIPE_COMMAND_RUNTIME_6828F209_2026-10-05.md)、[native来歴記録](NATIVE_BUILD_ATTESTATION_2026-10-04.md)も参照する。

共有環境への今回反映は別の対象固定・検証・承認が必要。復旧時は単純revertでtelemetry防止も外れることに注意し、opt-outを維持した修正版を優先する。既存実データ/識別子/ログの削除は行わず、必要なら別途対象と承認を確定する。実Stripe/RAK/共有DB/worker/メール、管理者運用選択、外部連携、AWS性能/復旧、事業者/税務条件を含む[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は未達。

## 隔離証拠の所在とSHA256

ログ等はGit外の `C:/tmp/iaia-background-telemetry-20261005/` に保持する。

| ファイル | SHA256 |
|---|---|
| native-default.log | 5772279b2fb882c8a2d5a30416146e22bd8bf506ca2763d5c5f9fcc0f0b7799e |
| native-optout.log | 97b85d3d8f54b38bec98e51a2fa3ab8c7da6c7a07179251e0e5ff37a340ad450 |
| native-inference-default.log | c070864cd0c3511a67765d514bc9d63ddfed4d5828b3486e56d063007adb8d94 |
| native-inference-override.log | 3d9a589145dd3472c83bc97660b8f77da81cf0f9d51cc7a25c18255e849ccaad |
| coverage-final.json | f1c6f1eaed3f9c966951ff542e4f9b823004dbf70ab3c3a3fb79454e6828fcb8 |
| final-regression.log | 3e44713cfca5149fad47b0bdf58b3af04586d80e12e100fd7ee4a7c8aeaa8b94 |
| inspection.json | 3fe122154e8f5880e9b17a09e0d29b1e0ae6ad8760034501048f7941723a3c21 |
| bandit-final.json | a5c5f8f0b466e0b6854ae2ed16517deb60584cddbfbc7baeb5ef2325ab278608 |
