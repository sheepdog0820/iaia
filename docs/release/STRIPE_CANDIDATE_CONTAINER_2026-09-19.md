# 候補99acd8caのコンテナ・DB互換性検証

2026-09-19。対象は `99acd8ca4d319c2579f74e4c1a102815ccd4a668`。作業ツリーがcleanであることを確認してビルドした。
ローカルイメージ: `tableno:stripe-candidate-99acd8ca`。
イメージID: `sha256:af0e52839ab52b4c5af3f0fd4e1087b0b58c1d24d4af1fd2d883ea8729601c32`。

## 検証

1. 実AWSと同じ旧版digest `sha256:59542e45e5dc8e1e33cbf7202eb12911ffbb390156a778fe7eb11f0fe4c65f79` をローカルで確認。
2. 外部接続できないDockerネットワークと、AWSと同じPostgreSQL 18.3を使用。旧イメージで全マイグレーションと架空利用者・契約・課金失敗監査を作成。
3. 新版の移行計画はaccounts 0065・0066・0067の3つのCreateModelのみ。適用・migrate --check成功。
4. 移行前後で利用者・契約・失敗時刻・監査が一致。
5. 新規3テーブルに架空の購入要求・請求状態・配送待ちメールを作成。旧版のcheckと既存データ読出しが成功。新版に戻しても新規記録を維持し、ログインした利用者の課金ページがHTTP 200。
6. 通常entrypointで新版ASGIサーバーを起動し、コンテナ内からHTTP readinessがok、DB・cacheもok。初回のホスト公開ポートを読む検証は内部ネットワーク上でport mappingを取得できず失敗したため、同じ隔離ネットワーク内でHTTP確認に変更した。外部ネットワークへの接続を許可したものではない。
7. pg_dumpのcustom形式を別の使い捨てDBへpg_restore。旧データ、新規3テーブル、再送用idempotency key、配送待ち状態が一致。復元後もmigrate --check成功。
8. イメージ内の共通の秘密設定・秘密鍵・SQLite・Terraform stateファイル名を確認し、該当なし。.gitも除外。これは秘密情報全体やOS脆弱性の網羅的スキャンではない。

全8項目の判定はSTRIPE_CANDIDATE_CONTAINER_RESULT_2026-09-19.jsonに記録。Web/DBコンテナを停止し、専用ネットワークも削除した。イメージとこのローカル検証記録のみ保持する。DBは架空の試験データのみで、共有DB・実ユーザー・AWSリソース・Secret・Stripe契約・外部メールへの変更はない。

## 限界と次の反映条件

ローカルでのスキーマ追加互換性・起動・DB論理バックアップ復元の検証である。RDSスナップショットからのサービス全体復旧、S3復元、RPO/RTOの証明、ブラウザからの決済完了、AWS常設worker/beat稼働、実配送は含まない。
旧版に戻す際も追加テーブルは残す方針であり、逆マイグレーションによる未配送記録削除は試験していない。共有反映時は新定義の単発タスクでDB変更を先に適用し、成功後にサービスを切り替える計画を用意する。現AWSの稼働イメージと設定を切戻し先として保存する。

同じ候補のGitHub Actions run 35431750178は6ジョブすべてsuccessで完了した。STRIPE_CANDIDATE_CI_2026-09-19.jsonを参照。正式公開はまだNo-Go。

## 最新の判定と参照

この文書の検証対象は99acd8caで固定する。この記録を追加した文書ブランチのCIとは区別する。[対象SHAのCI](https://github.com/sheepdog0820/iaia/actions/runs/35431750178)は6ジョブ成功。mainへのマージ・開発AWSへの反映は未実施で、[アプリ反映案](STRIPE_AWS_APP_APPROVAL_2026-09-19.md)を提示して承認待ち。

追加の読み取り確認で、Terraform state serial43はWeb定義36、実稼働は49であること、AWSの既存StripeテストキーでGET /v1/accountがAuthenticationErrorとなることを確認した。[秘密値を除いた確認結果](STRIPE_AWS_CONFIGURATION_2026-09-19.json)を記録した。キーがローカルと異なることだけでアカウント不一致とは判断していない。AWSキーではアカウントを特定できなかった。SMTP認証項目は存在するが、認証・配送は未検証。

正式公開の残条件は常設worker/beat・broker、Stripeテスト接続設定の修復、AWS実フロー、メール配送・監視、他の外部連携・性能・復旧等。[受入条件表](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を参照。CI成功や今回のDB論理復元だけで全体を完了扱いしない。
