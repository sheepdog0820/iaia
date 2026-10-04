# 課金レコード管理フォームの更新整合性（2026-10-04）

## 調査・再現

先行[手動プレミアム設定](MANUAL_PREMIUM_INTEGRITY_2026-10-04.md)の後、独立したPremiumSubscriptionAdminの直接編集を専用ブランチ `codex/subscription-admin-save-integrity-20261004` で確認した。元checkoutのハンドアウト差分は保持した。

既存フォームは全モデルを保存するため、未編集の契約状態/Stripe IDだけでなく、読み取り専用の支払失敗/返金検知日時/最終Webhook IDも古い値へ戻した。削除後の古いモデル保存は課金レコードを再作成した。保存列の限定だけでは、GETからPOSTの間に変わった状態をPOSTフォームが変更済み入力として解釈する問題を防げない。

- 修正前のSQLite11件は4成功・7メソッド失敗（subTestを含む失敗出力9件、1.054秒・終了1）。古い値の書き戻し、削除後の再作成、更新確認の欠落/改変/別レコード/GET後更新の受け入れを検出した。
- 修正前のPG競合1件は共有ロックへ到達せず失敗（10.161秒・終了1）。待機用Eventの10秒上限が失敗理由であり、通信障害やStripe実APIの結果ではない。
- 最初の修正後はSQLite11件成功、PG12件成功。精度・検証後の再確認・管理ログ・既存操作・実フォーム競合等を追加した最終22件を含め、下記の関連回帰へ広げた。

## 修正と維持した仕様

- GET時の全具体列（readonlyを含む）を、日時のマイクロ秒精度を保ってSHA-256 digest化する。レコードPKとdigestだけを既存Django signingで署名し、hiddenの更新確認情報として渡す。Stripe IDや日時そのものを新たにtokenへ露出しない。更新日時を変更しないwriterも検出する。
- POSTのフォーム検証で共有課金行をFOR UPDATEし、署名・対象PK・全列digestを照合する。旧版/別対象なら「課金情報が変更されています。ページを再読み込みして、内容を確認してから保存してください。」、欠落/改変なら「更新確認情報が無効です。ページを再読み込みしてください。」と表示し、保存/管理ログを行わない。
- 通常Django adminの既存外側transactionは、フォーム検証から保存・関連保存・管理ログ・commitまで継続する。新規save_modelもatomicにし、行を再取得してモデルフォームの更新確認を再照合する。削除済み行は404で拒否し、再作成しない。フォームを外側transactionなしで検証した後に使う呼出でも古い保存を拒否する。
- 実保存はフォームのchanged_dataと具体列の交差だけ。変更時のみupdated_atを更新し、変更なしでは古い列/更新日時を書き戻さない。確認情報はchanged_data/管理ログから除外する。ログ失敗時は既存admin transactionで変更もrollbackされる。
- 新規追加、明示的な変更、期間末解約チェックの解除、Django adminの実行者/変更列ログ、認可/CSRF/フォーム検証、既存の停止・復旧・再同期アクションを維持する。保存による暗黙のユーザー権限再同期やStripe契約変更は追加しない。フォームなしの従来呼出は明示的な全モデル保存として維持し、任意の管理スクリプト全体の競合安全性を保証しない。

独立課金レコードの直接削除・ユーザー付け替えと、Stripe/請求/購入画面/配送記録の所有関係は今回変更していない。その運用と安全性の確認は残る。今回の更新保護を管理者の全経路の合格に拡張しない。

`stripe-best-practices`の隔離検証・非同期課金状態保護の方針を使用した。実Stripe API/署名Webhook・SDK/APIバージョン・Client方式・Price・キー・税設定を変更しない。本番の販売対象/税務・外部連携の確認は別途残る。

## 最終検証

| 環境 | 1実行の結果 | 時間 |
| --- | --- | --- |
| Windows Python3.11.1 / Django5.2.17、SQLiteメモリDB | 379件中361成功・既存行ロック18省略・終了0 | 41.365秒 |
| Linux、隔離PostgreSQL18.3、coverage付き | 394成功・省略0・終了0 | 65.892秒 |

新規22件は一般19件・PG専用3件。SQLiteでは今回3件と先行手動設定9件/管理操作3件を対象外にした上で、選択済み既存18件が省略された。対象外/省略を成功数へ含めず、途中の11/12/18/21件は重複するため最終数へ加算しない。

範囲は新規フォーム、先行管理操作/手動設定、billing・課金競合・退会ガード・paid_feature_lifecycle・コード直列化/失効/再同期・メール配送/監視・Portal/複数停止理由/Invoice/Event/Dispute/Checkoutの順序/再試行/復旧。異常系の403/500/503等は期待結果で、予期しない最終試験エラーはない。

Django Test Clientの実GET/POSTで、更新確認のhidden表示、欠落/改変/別対象/不正payload/マイクロ秒差の拒否、通常編集/変更なし/readonly列のPOST偽装/新規追加/権限拒否/管理ログrollbackを確認した。PG3件では直接部分保存がwriterのcommitを待つこと、フォームPOSTがwriterを待ってから旧版を拒否すること、保存から管理ログのcommitまで課金行を保持することをEventと別DB接続で確認した。ブラウザー描画・Socket HTTP・実Stripe・AWS検証ではない。テンプレート/リンク/ボタン/CSS/JSの変更はない。

最終coverage7.15.4（Python/thread tracer）で、変更save_model18文/8分岐、新規billing_admin_forms全体44文/6分岐、新規テスト337文/20分岐が100%。admin全体・全課金/認可経路の100%ではない。初回coverageのC tracer未導入警告はPython tracerへフォールバックし、最終実行では明示pytraceにした。途中の新規テストでは未実行のチェックボックスTrue分岐を検出し、期間末解約チェック解除の正常系を追加して最終100%を確認した。

初回Windowsの失敗ログにはコンソール文字コード由来の日本語表示崩れがあり、以降PYTHONUTF8/PYTHONIOENCODINGを明示した。ソースの日本語/期待値を英語に置換せず、UTF-8で読んだ差分と重要メッセージのassertで確認した。調査時のWindows rgへの未展開globや存在しないsettingsファイルの読み取り失敗は工具側の失敗で、現存ファイルを調べ直した。

Black/isort/Flake8、Bandit対象3ファイル（0指摘・0解析エラー）、Django check、makemigrations --check --dry-run（変更なし）、workflow YAML/必須PG対象指定を確認した。新しい日本語ラベルと4エラー文、既存英語ラベル/技術トークンの不変更をレビューした。署名・粒度・ロック保持・rollback・認可・readonly・正常系/互換性を自己レビューし、この修正単位に未解消指摘はない。ステージ済み6ファイルの全差分/UTF-8/LF/文字化け検査と文書のローカル参照も確認した。

## 環境・証跡・反映境界

専用PGはnetwork none・公開ポートなし・512 MiB・DBデータtmpfs。ENV_FILE空、APP_ENV=local、合成SECRET_KEY/利用者/Stripe ID、locmemメール/cacheで隔離した。専用試験DBは各実行後Djangoが破棄する。既存通常イメージ `sha256:46795320922764a1bc2065f8c161e8d317cb0f2f5c1588a6d9026660d4a666f4` に今回ソースとcoverage工具をreadonly mountした試験であり、修正後の通常配布物の証明ではない。

専用PGのID/名前/networkを再照合して停止・削除した。合成tmpfsデータはfixtureから再作成可能で、設定・ログ・coverageは `C:/tmp/iaia-subscription-admin-20261004` に保持する。

| 証跡 | SHA-256 |
| --- | --- |
| coverage-final.json | 51324eb0a76b1211944bdb8575d209dfe3bbf228eeca577ef385f409c2e5b278 |
| bandit-final.json | 9ae0b421e00a7138e08c0406a18e15643e9a4e2c0a8e25ce1e25fd4e73c14804 |

先行 `f543f784c60a422f2a2c669a232fe10052dcde98` の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37193659691)をhead SHAと照合した。今回候補のCI/通常配布物/AWSは未確認。mainは8567f49fと読み取り確認し、main/ECR/ECS/S3/CloudFront/共有DB/実データ/Secrets/IAM/課金有効化/容量/継続費用を変更していない。pushのworkflowはCIのみでAWS反映処理はない。固定承認案6b6c570cへ追加しない。

復旧はfix-forwardを優先する。今回コミットのみのrevertは可能だが、古い契約状態の上書き/レコード再作成を再導入するため、そのまま正式公開しない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
