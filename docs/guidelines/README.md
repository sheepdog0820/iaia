# 開発ガイドライン

このディレクトリには、Arkham Nexus (iaia) プロジェクトの開発ガイドラインが整理されています。

## ガイドライン一覧

### 🎯 キャラクターシート開発
- [CHARACTER_SHEET_GUIDELINES.md](./CHARACTER_SHEET_GUIDELINES.md) - クトゥルフ神話TRPG専用キャラクターシート開発ガイド

### 🔧 JavaScript開発
- [JAVASCRIPT_GUIDELINES.md](./JAVASCRIPT_GUIDELINES.md) - JavaScriptのスコープ管理とエラー防止ガイド

### 🧪 テスト駆動開発（TDD）
- [TDD_GUIDELINES.md](./TDD_GUIDELINES.md) - 厳格なTDD実践ガイド

### 🖥️ UI/UX開発
- [UI_REFACTORING_GUIDELINES.md](./UI_REFACTORING_GUIDELINES.md) - 画面リファクタリングと段階的改善ガイド

### 🔄 画面遷移チェック
- [NAVIGATION_CHECK_GUIDELINES.md](./NAVIGATION_CHECK_GUIDELINES.md) - 画面編集時の必須遷移チェックガイド

### 📋 課題管理
- [ISSUE_MANAGEMENT_GUIDELINES.md](./ISSUE_MANAGEMENT_GUIDELINES.md) - ISSUES.mdを使った課題管理と進捗追跡ガイド

## 用途別参照ガイド

### 新機能開発時
1. 📋 [ISSUE_MANAGEMENT_GUIDELINES.md](./ISSUE_MANAGEMENT_GUIDELINES.md) - 課題確認
2. 🧪 [TDD_GUIDELINES.md](./TDD_GUIDELINES.md) - TDDプロセス
3. 🔧 該当する技術ガイドライン

### キャラクターシート作業時
1. 🎯 [CHARACTER_SHEET_GUIDELINES.md](./CHARACTER_SHEET_GUIDELINES.md) - 制限事項確認
2. 📋 [CHARACTER_SHEET_FEATURES.md](../../CHARACTER_SHEET_FEATURES.md) - 実装済み機能リスト確認
3. 📐 [SKILL_TAB_SPECIFICATION.md](../../SKILL_TAB_SPECIFICATION.md) - 技能タブUI実装時の参照
4. 🧪 [TDD_GUIDELINES.md](./TDD_GUIDELINES.md) - テスト作成

### JavaScript修正時
1. 🔧 [JAVASCRIPT_GUIDELINES.md](./JAVASCRIPT_GUIDELINES.md) - スコープ管理
2. 🔄 [NAVIGATION_CHECK_GUIDELINES.md](./NAVIGATION_CHECK_GUIDELINES.md) - 動作確認

### 画面修正時
1. 🖥️ [UI_REFACTORING_GUIDELINES.md](./UI_REFACTORING_GUIDELINES.md) - 段階的改善
2. 🔄 [NAVIGATION_CHECK_GUIDELINES.md](./NAVIGATION_CHECK_GUIDELINES.md) - 遷移チェック
3. 🔧 [JAVASCRIPT_GUIDELINES.md](./JAVASCRIPT_GUIDELINES.md) - JS動作確認