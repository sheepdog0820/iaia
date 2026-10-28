# Checkout・請求管理の所有者と再試行の整合性（2026-10-28）

## 対象と問題

正式公開はNo-Goを維持する。[課金編集のPR #14](https://github.com/sheepdog0820/iaia/pull/14)のhead `230837db810a3b851ba69f576f69c1a3166ca4d3` を基点に、別ブランチ `codex/billing-request-owner-followups-20261028` で既知 `f4ea34ca` の製品差分と回帰だけを選んだ。対象は顧客作成・Checkout・請求管理ポータルの、ローカル課金行と保存済み再試行要求の対応確認である。

最初の取得後に課金行の所有者や顧客IDが変更された場合、古い対応のまま処理が進んだ。保存済み要求のmetadata・顧客ID・参照ユーザー・購読metadataが別ユーザーを指す場合も、再試行前に確認していなかった。ポータルの作成も共有行ロックの外にあり、対応確認と作成が食い違う余地があった。実ユーザーの不正利用や実課金事故が発生したことを確認した記録ではなく、合成データで不足を再現した調査である。

## 修正

- 各作成/再試行の課金行ロック後に、所有者が要求ユーザーと一致することを確認する。顧客IDも最初に組み立てた要求と現在の行で一致し、空でないことを確認する。
- 保存済みの顧客/Checkout要求のmetadataを確認し、Checkoutでは顧客ID・client_reference_id・subscription_dataのユーザーIDも同じ所有者に対応することを確認する。欠落・不正形式・別所有者なら、外部作成や新しいURLの返却へ進まない。
- 2段階の顧客作成は両段階で再確認し、Checkoutも繰り返しの各ロック取得後に再確認する。ポータルは対応確認から作成まで同じ課金行ロックを保持する。顧客/Checkoutの外部作成と結果保存の既存ロックも維持する。
- 不一致時は日本語のAPI 400を返し、リソースURLを返さない。既存の再試行キー・パラメータを消去/再作成せず、結果不明や反復上限の場合も保存済み要求を保持する。料金・プロフィールの再計算で、過去の不確定な要求の内容を変えない。
- PostgreSQLのCI対象へ回帰ファイルを追加する。新しいStripe API呼び出しや送信先、SDK/依存ロック・API版は追加/変更しない。

対応不一致の要求は自動修復しない。調査後に実データを修正する必要がある場合は別の承認対象とする。ローカル行・要求の対応の保護であり、実Stripeアカウント/リソースの再照合、StripeClient設定の分離やSDK/API更新、実AWSの有料受け入れを完了にするものではない。

## 検証

固定依存のPython 3.11.18 / Django 5.2.17 / PostgreSQL 18.3を使用。専用label・internal network・公開ポートなしのローカル使い捨てDBを毎回照合し、実データと外部通信なしで検証した。Stripeへの参照はmockのみで、実顧客・Checkout・ポータル・課金を作成していない。

修正前は41失敗・6成功（失敗数にはsubtest失敗を含む）。修正後の対象は **22テスト・25 subtests成功、省略なし**。不一致の各段階・不正な保存形式・所有者の変更/移管、結果不明の再試行保持、APIの日本語エラーとURL非返却を含む。実PostgreSQLの6件の別接続試験で、課金行の更新を待った後の再確認と、作成呼び出し/結果保存までのロック保持を確認した。

Black/isortは対象2ファイルだけを確認して変更なし、Flake8/Bandit成功。新しいAPI表示文は日本語で、実API応答の完全一致でも検証した。初回の局所網羅率確認では、既存のポータル設定IDの回帰で通す追加行が一件残ったため、既存課金試験を含めた後続の実行で照合する。全billingモジュールの100%を主張しない。

証跡はGit管理外 `tmp/billing-owner-pg-red.log`、`tmp/billing-owner-pg-green.log`、`tmp/billing-owner-pg-coverage/coverage.json` 等に保持する。関連課金回帰・SQLite・通常配布物・CIの最終結果は後続の記録で区別する。

最初の関連11ファイルの試験は340成功・2失敗だった。新しい試験のcore側mockが、初回のview importでWebhookの参照へ残り、署名付きWebhookの既存2試験へ干渉したことを確認した。製品の所有者チェックを緩めず、追加fixtureでviewをcoreより先に読み込んで両方のpatchをcleanupするよう修正した。同じ順序のAPI/署名付きWebhook3テスト・10 subtestsが成功した。

その後、既存の再試行・Webhook/返金/支払イベント順序の9モジュールも含めた **20モジュール、396テスト・84 subtestsが実PostgreSQLで成功、省略なし**。追加/変更実行文は **39/39** を通過し、当初の設定ID用の行も既存の正の回帰で通過した。billing全体は約96%であり、全体100%とはしない。SQLiteも修正後の16テスト・25 subtests成功、ロック等が必要な6件のみ意図して省略し、同じ6件はPostgreSQLで成功した。証跡は失敗を保持した `tmp/billing-owner-pg-broad.log`、原因確認/修正の `tmp/billing-owner-webhook-isolation-green.log`、最終の `tmp/billing-owner-pg-final.log` と `tmp/billing-owner-sqlite-final.log`。試験内のStripe参照はmockまたは合成署名のローカル検証であり、実サービスへの送信は行っていない。通常配布物・最終CIは別途照合する。

### 通常配布物

製品修正 `21f8d60177266cd116589d1275f04bc229c88014` を通常push後、そのgit archiveから通常Dockerfileで構築した。タグ `tableno:release-candidate-21f8d601`、イメージID `sha256:3c8280d4f3098b297d00676cd50917fb5a52ea864cf980f0548d8f6e3bf92024`。製品ソース・固定依存・試験・entrypoint等35ファイルと実entrypointのGit blob一致を確認した。

配布物内でも同じ20モジュールの **396 Djangoテストが実PostgreSQLで成功、省略なし**。合成設定ファイルだけを渡し、製品ソースbind mount・pip/pytest追加なし、UID10001・読み取り専用・外部通信なしで実行した。証跡は `tmp/billing-owner-normal-image-build.log`、`tmp/billing-owner-normal-runtime.log`、`tmp/billing-owner-normal-source-manifest.json` に保持する。実Stripeや実ユーザーの操作、OS再監査・ECR push・実AWS反映は行っていない。

[Draft PR #15](https://github.com/sheepdog0820/iaia/pull/15)はPR #14をbaseとし、製品修正と後続の検証資料コミットを区別する。最終CIはChecksで照合し、CI待ちの候補をマージ可能とは扱わない。

## 承認と復旧

実ユーザーの課金/権限・実Stripe・実AWS・外部通知は操作していない。DBスキーマ/移行、Secrets/IAM/OAuth、料金・保持期間・常設資源/費用の変更はない。作業ブランチの通常push・Draft PRまでを進め、先行PR後のbase変更と最終head・差分・CIを照合し、mainへの追加マージを別途承認してもらう。

復旧は対象コミットのrevert PRだが、対応の違う要求が作成へ進む問題やポータルの競合を再導入する。有料必須ゲート、外部連携・OS監査・性能・復旧等の正式公開条件を維持する。
