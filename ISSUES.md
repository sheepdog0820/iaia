# Tableno 未完了課題

最終監査日: 2026-06-12

このファイルは未完了の正式課題だけを管理します。完了項目は `ISSUES_CLOSED.md`、現行機能は `docs/CURRENT_WEBAPP_FEATURES.md`、セッション領域の分類は `SESSION_UNIMPLEMENTED_FEATURES_SPEC.md` を参照してください。

## 優先度: 高

### ISSUE-010: テスト品質ゲートの拡張

- 境界値・異常系テストの追加
- 負荷・パフォーマンステスト
- カバレッジ計測をCIの必須ゲートへ統合

### ISSUE-056: AWS実環境への適用とGo/No-Go

- `infrastructure/terraform/` の `aws-pre` / `aws-prod` への実適用
- DNS、ACM、Secrets、通知先、予算上限の実値設定
- メディア・DB移行Runbookの実データリハーサル
- CloudWatch Alarm通知、バックアップ復旧、RPO/RTOの実測
- 実AWSアカウントと承認が必要なため、リポジトリ内実装とは別の運用工程として扱う

## 優先度: 中

### ISSUE-046: セッション状態スナップショット

- 開始時HP/MP/SANスナップショット
- セッション中の変動履歴
- 終了時差分と状態異常・一時効果

### ISSUE-057: 外部連携の運用強化

- Google OAuth refresh tokenのローテーションと失効復旧UI
- Google Calendarの双方向同期・競合解決
- Sheetsの大規模インポート/エクスポート進捗UI
- Discord配信失敗の管理画面と手動再送

### ISSUE-058: 公開募集ページ

- 招待URLによるゲスト参加とclaimは実装済み
- 空き枠検索、締切、承認制を備えた横断募集ページは未実装

## 優先度: 低

### ISSUE-027: ネイティブモバイルアプリ

- iOS/Androidアプリ
- ネイティブPush通知
- オフライン同期

### ISSUE-029: AI分析・推奨

- プレイスタイル分析
- シナリオ推奨
- セッションマッチング

## 将来候補

- セッション掲示板
- クイック投票
- 汎用素材ライブラリ
- VTT連携

将来候補は受け入れ条件と優先順位が確定するまで正式課題へ昇格しません。
