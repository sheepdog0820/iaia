# Stripe API版・Webhookのmain後続修正（2026-10-28）

## 対象と利用者への影響

PR #16の14ff9259を基点に、既知2b70f1d5からAPI固定・イベント対応・運用照合を分離する。過去の依存ロックや正式公開済みという扱いは取り込まない。現在の3ロックのうちStripeだけを15.5.1から16.0.1へ更新し、他のセキュリティ更新は保持する。依存宣言は`stripe>=16.0.1,<17`へ揃える。

APIリクエストの既定は`2026-09-30.endive`へ明示固定し、環境変数による既存の指定は保持する。空白の指定はSDKやアカウント既定へフォールバックせず、日本語の設定エラーにする。Stripe上のアカウント既定・Webhook版・実Secretsを変更する操作ではない。

新規Checkout intentは追跡ラベルを一度だけ保存し、応答消失時にも本文・冪等キーを維持する。既存ラベルなしintentへ後付けしない。ラベルはAPI上任意であり、Stripe実装ガイドの指定に従うもので、料金や購入権限の識別には使わない。旧API指定には非対応パラメーターを送らない。

署名付き`customer.subscription.paused/resumed`は、取得し直した最新契約を使って権限同期する。`pause_collection`とは異なる。`invoice.paid`はStripe外での入金済み記録も含むため、イベント名だけで権限付与せず、最新請求・他の未解決請求を確認する。手動・コード付与や返金等による停止方針は維持する。

読み取り用のremote checkは同じ送信先の有効なWebhook版をすべて照合し、アカウント既定/不明・異版を拒否する。無効な旧送信先が有効な置換先より前に列挙されても誤って拒否しない。必須イベント・実検証記録テンプレート・運用手順を更新する。

## 検証

- 修正前の実SDK・メモリ内HTTP transportによる回帰は16失敗・4成功。無効な重複送信先が先頭のケースも追加し、修正前の1失敗を確認した。
- SDK16.0.1を公式PyPIのSHA256で検証し、外部通信なしで検証イメージへ導入した。`pip check`成功。実決済HTTPはFixtureTransportだけを使う。
- 初回の関連PG20テスト・3 subtests成功。追加した日本語APIエラー、再開時の自動停止保持、古い入金通知、別請求の未解決警告を含む最終SQLite25テスト・3 subtests成功。関連26モジュールの隔離PG513テスト・113 subtests成功、省略なし。既存の認証・退会・所有者/ロック/監査、実SDK署名・ページ送り・並行クライアント・運用ゲート・文書も含む。
- 本番設定の別プロセスprobeを含む55テスト・3 subtests成功。変更実行文は課金/remote check/設定の24/24を通過。定数のイベント追加は既存の代入文行へ集約されるため、変更実行文の分母へ水増ししない。製品全体100%とはしていない。親プロセスのsettings_production未import警告はあるが、合算JSONには別プロセスの設定計測を含む。
- 3ロックはStripe以外の版がすべて不変で、固定ハッシュは公式配布物と照合した。pip-audit 2.10.1によるruntime111・dev167・test207依存の監査はいずれも既知指摘0、exit 0。OS指摘を解消したという意味ではない。
- 製品修正ddbb6115のgit archiveから通常Dockerfileで構築した。image IDは`sha256:8b0283c2ec119674b9a9b93f528bade8e16367798623c1301d43d5b96ad2b95a`。54ファイルと実entrypointのGit blob一致、アプリ/設定26モジュールの504 Djangoテストが配布物内で成功、省略なし。合成設定だけを渡し、製品ソースbind mount・pip/pytest追加・計測pluginなし、UID10001・読み取り専用・外部通信なしで実行した。ソース環境の文書39テストはAGENTS.mdを意図して含めない通常配布物から除き、本番設定30件を追加したため、513-39+30=504として範囲を区別する。最終CIと新イメージのScout監査は確認中。
- 対象Python10ファイルだけにBlack/isortを実行。Flake8/Bandit成功。既存の不要なnosec警告は残り、新しい抑制は加えていない。

## 承認・未確認・復旧

この枝のコミット・通常push・Draft PRはAWS反映を起動しない。main追加マージ、AWS反映、実Webhookの作成/版変更、Secrets・権限変更、実データ操作・課金試験は未実施で、別途具体的な対象を確認する。DBモデル/マイグレーション、既存料金、常設資源・継続費用は変更しない。

実Stripeとの互換性、実AWSでのCheckout→帰着→Webhook→権限・メール・解約、有料必須ゲート、外部連携、OS指摘、性能、DB/S3復旧などは未完了。正式公開No-Goを維持する。合成成功を実受け入れへ読み替えない。

復旧はこの差分をrevertするPRと直前イメージへの別承認の反映。外部API/Webhookの版を別途変更した場合は、その復旧も対で計画する。保存済みCheckout本文・冪等キーは手作業で書き換えず、未確定要求を照合する。旧SDKの証明書バンドルも戻る点を復旧判断に含める。

## 公式根拠

- [SDK16.0.1変更履歴](https://github.com/stripe/stripe-python/blob/v16.0.1/CHANGELOG.md): 証明書バンドル更新、16系の互換性変更。
- [固定SDKのAPI版](https://github.com/stripe/stripe-python/blob/v16.0.1/stripe/_api_version.py): Endive。
- [API版](https://docs.stripe.com/api-versions)、[版の設定](https://docs.stripe.com/sdks/set-version)、[アップグレード](https://docs.stripe.com/upgrades)。
- [Checkout作成](https://docs.stripe.com/api/checkout/sessions/create)、[イベントの種類](https://docs.stripe.com/api/events/types)。
- [受け入れ条件と先行PR](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)。

公式公開文書は認証情報を持たない専用CLI設定から読み取り、Stripeアカウント・Sandbox・APIキーは作成していない。接続プラグインの再認証が必要な状態を実検証済みと扱わない。
