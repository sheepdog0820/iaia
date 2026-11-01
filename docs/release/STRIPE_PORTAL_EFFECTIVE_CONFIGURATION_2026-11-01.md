# Portalの実効設定に合わせた事前検査

## 問題と修正

アプリは `STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID` を指定した場合だけPortal sessionの `configuration` を渡し、未指定ならStripeの既定設定を使用する。従来の外部事前検査は全active設定を対象にしていたため、既定設定の機能が不足しても他設定の機能を合算して成功できた。モード検査と機能検査の対象も同一に拘束されていなかった。

設定ID指定時はその設定を直接retrieveし、最初の100件から探す方法をやめた。未指定時は `is_default=true` でlistし、一意な既定設定を選ぶ。同じ1件のactive/mode/3機能を確認する。設定なし・複数・途中までの一覧・ID/モード不明や不正な型を成功にしない。機能のenabledはboolean trueを要求する。明示IDが非既定でも、アプリの選択どおり検査できる。

実Portalの設定・session作成処理・料金・契約/権限・SDK/API版・DB schemaは変更しない。従来通っていた不適切な設定では検査commandが失敗するが、Stripe側を自動修復しない。取得時の404などは既存のSDK例外保護を通して表示し、providerの私有本文は出さない。

## 検証

テスト先行で旧実装の23失敗/1errorを確認し、Portalの選択・機能合算・モード・型・一覧の完全性を修正した。SDK objectとcommandの検査に加え、固定SDKのHTTP clientを模擬し、実際のGET URL・`is_default=true`・明示IDの直接取得を検査する。実ネットワーク・APIキー・本物のPortal sessionは使わない。既存fixtureには既定設定の属性を追加し、明示IDのfixtureをretrieveへ揃えた。

最終のテスト件数、coverage、整形・静的解析、通常配布物内とCIの結果はPRに記録する。日本語の新規CLIメッセージとUTF-8/LF・差分・ソースをレビューする。

## 実環境・承認・復旧

共有AWS・Stripe設定・Secrets/IAM・実ユーザー・費用・外部通知・公開は変更していない。新しいマイグレーションはない。復旧はrevert PRだが、実際と異なるPortal設定を事前検査で合格させる問題も戻る。

既知sandboxのtest料金/Portal機能の読取一致は、AWSの実効設定や実購入/SMTP配送の合格ではない。元25条件・OS53指摘と正式公開No-Goを維持し、mainマージ・実環境反映は別の承認対象とする。税務/税表示・保持方針などの公開前判断も維持し、課税設定は変更していない。

## 公式仕様

- [Portal session作成：configuration省略時は既定設定](https://docs.stripe.com/api/customer_portal/sessions/create)
- [Configurationのactive / is_default / livemode](https://docs.stripe.com/api/customer_portal/configurations/object)
- [設定一覧のis_default filter](https://docs.stripe.com/api/customer_portal/configurations/list)

公開参照の最新API表示版を自動採用せず、承認済みのSDK16.0.1/API 2026-09-30.endiveを維持する。
