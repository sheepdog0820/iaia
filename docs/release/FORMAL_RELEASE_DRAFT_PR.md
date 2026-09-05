# 正式公開に向けた課金・認証・秘匿情報保護の修正と検証

Base: main / Head: codex/delegated-workflow-rules / Draft: true

有料プラン・外部連携を含む正式公開に向け、課金、認証、秘匿添付、キャラクター管理の不具合を修正し、公開判定の証拠と未完了事項を整備します。正式公開の条件は未達のためDraftです。

主な変更:
- Stripe SDKイベント形式・期間終了日時・DB障害時のWebhook再試行に対応し、有料Checkoutの必須ゲートを整備。
- Googleの安定した外部IDによる照合とメール確認を徹底。X/Discordを含む登録保存を原子的にし、停止済み利用者、競合、障害時の機密ログを対策。
- 秘匿HO・セッション/シナリオ画像の取得時認可と旧URLの保護、削除障害時の参照保持。CloudFront迂回防止のTerraform案は未適用。
- 技能一括保存の部分成功を廃止し、ポイント再配分を可能にする。画像検証後の読み直し失敗と一覧の代替画像選択を修正。
- 外部出力時の権限再確認、HTTP timeout、ICSの日本語折り返し、一覧取得の効率化、開発コマンドの環境制限を整備。

検証:
- d572a618の固定ソースでSQLite/PostgreSQL全体テストを実行中。終了結果は未取得。
- 同SHAの通常Dockerfile/固定依存による配備用イメージを構築。隔離PostgreSQL16/Redis7で全移行、静的収集、通常起動、ヘルス200、pip check、check --deploy成功。
- 最新Banditは解析エラー0、HIGH/MEDIUM 0、LOW556。個別分類と残作業を文書化。
- 過去58a27172の全体成功は後続修正の合格証拠に流用しない。各修正は関連回帰テストを実施。
- 詳細: docs/release/FORMAL_RELEASE_AUDIT_2026-09-05.md、FORMAL_RELEASE_ACCEPTANCE_MATRIX.md。

公開前の残作業:
料金・有料範囲の判断、実Stripe/OAuth/外部配送、候補全体の終了結果とリモートCI、実環境のストレージ/CDN対策、性能・復旧/ロールバックの実証。実料金・規約や公開時期は未確定です。本PRの作成はmainマージ、本番反映、共有DB・実データ・権限・費用変更の承認を意味しません。

作成状況: 2026-09-05に対象ブランチのPR検索は0件。作成APIは403 Resource not accessible by integrationで拒否。PRは未作成。GitHub CLIも未ログイン。StripeはUNAUTHORIZED/oauth_token_invalid_grantで再認証が必要。
