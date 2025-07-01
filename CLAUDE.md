# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 📁 ガイドライン体系

詳細なガイドラインは用途別に整理されています。作業内容に応じて適切なガイドラインを参照してください。

### 🔍 作業別ガイドライン参照

| 作業内容 | 参照ガイドライン |
|---------|-----------------|
| **新機能開発** | 1. [課題管理](docs/guidelines/ISSUE_MANAGEMENT_GUIDELINES.md)<br>2. [TDD](docs/guidelines/TDD_GUIDELINES.md) |
| **キャラクターシート開発** | 1. [キャラクターシート制限事項](docs/guidelines/CHARACTER_SHEET_GUIDELINES.md)<br>2. [機能一覧](CHARACTER_SHEET_FEATURES.md) - 実装済み機能の詳細<br>3. [技能タブ仕様](SKILL_TAB_SPECIFICATION.md) - 技能タブUI仕様 |
| **JavaScript修正** | [JavaScript](docs/guidelines/JAVASCRIPT_GUIDELINES.md) |
| **画面・UI修正** | 1. [UIリファクタリング](docs/guidelines/UI_REFACTORING_GUIDELINES.md)<br>2. [画面遷移チェック](docs/guidelines/NAVIGATION_CHECK_GUIDELINES.md) |
| **テスト作成** | [TDD](docs/guidelines/TDD_GUIDELINES.md) |

詳細は [docs/guidelines/README.md](docs/guidelines/README.md) を参照してください。

## 🚀 クイックスタート

### 開発環境セットアップ
```bash
# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# データベースセットアップ
python3 manage.py migrate

# スーパーユーザー作成（自動化済み）
python3 create_admin.py  # ユーザー名: admin, パスワード: arkham_admin_2024

# サンプルデータ生成
python3 manage.py create_sample_data

# 開発サーバー起動
python3 manage.py runserver
```

### 基本的なコマンド
```bash
# テスト実行
python3 manage.py test

# マイグレーション
python3 manage.py makemigrations
python3 manage.py migrate

# 静的ファイル収集
python3 manage.py collectstatic --noinput
```

## 🏗️ プロジェクト構造

### 主要Djangoアプリ
1. **accounts/** - ユーザー管理と認証
   - カスタムUserモデル、グループ管理、キャラクターシート
2. **schedules/** - セッションとスケジュール管理
   - TRPGセッション、参加者管理、ハンドアウト
3. **scenarios/** - ゲームシナリオ管理
   - シナリオリポジトリ、プレイ履歴、GMノート

### テスト構造
```
tests/
├── unit/           # 単体テスト
├── integration/    # 統合テスト
├── system/         # システムテスト
├── ui/            # UIテスト
└── e2e/           # E2Eテスト (Playwright)
```

### テストケース・結果ドキュメント
- **保管場所**: `docs/test_results/`
- **UIテスト**: `docs/test_results/ui/` - キャラクター作成画面のテストケースと結果
  - テストケースファイル（実行可能なPythonコード）
  - テスト実行結果レポート
  - 機能改修時のテスト結果

## 🔧 技術スタック

- **Backend**: Django 5.0.9, Django REST Framework
- **Database**: SQLite (開発), PostgreSQL (本番推奨)
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Testing**: pytest, Selenium, Playwright
- **Authentication**: django-allauth (Google/Twitter OAuth)

## 📋 重要な制限事項

### キャラクターシート機能
- **対応システム**: クトゥルフ神話TRPG 6版・7版のみ
- **7版開発**: 現在保留中（6版完成後に開発開始）
- 他のTRPGシステムには対応しません

詳細は [キャラクターシートガイドライン](docs/guidelines/CHARACTER_SHEET_GUIDELINES.md) を参照してください。

## 🧪 品質基準

### 必須要件
- ✅ **TDD**: すべての機能はテストファーストで開発
- ✅ **カバレッジ**: 新規コードは100%カバレッジ
- ✅ **コード品質**: リンティング・セキュリティチェック通過
- ✅ **ドキュメント**: 実装内容の文書化

詳細は [TDDガイドライン](docs/guidelines/TDD_GUIDELINES.md) を参照してください。

## 📚 関連ドキュメント

### 仕様書
- [キャラクターシート6版仕様書](docs/character_sheet/CHARACTER_SHEET_6TH_EDITION_SPECIFICATION.md)
- [プロジェクト仕様書](SPECIFICATION.md)

### 管理ファイル
- [課題管理](ISSUES.md) - 現在の課題と優先順位
- [完了課題](ISSUES_CLOSED.md) - 完了済み課題のアーカイブ

### テスト関連
- [Seleniumインストールガイド](docs/SELENIUM_INSTALLATION_GUIDE.md)
- [E2Eテストセットアップ](docs/E2E_TEST_SETUP.md)
- [UIテストケース・結果](docs/test_results/ui/README.md) - キャラクター作成画面のテストドキュメント

## 🌐 環境情報

### 現在の環境
- Working directory: /mnt/c/Users/endke/Workspace/iaia
- Platform: Linux (WSL2)
- Git branch: main

### テスト済み環境
- Python: 3.10+
- Django: 5.0.9
- Node.js: 18+ (Playwright用)
- Chromium: 138.0.7204.49