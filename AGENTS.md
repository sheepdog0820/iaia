# AGENTS.md

このファイルは、Codex (Codex.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## Codexへの作業委任と承認境界

### 役割と進め方

- 人間は目的・優先順位・価値判断・権限・利用者への約束・最終責任を担当する。Codexは依頼された目的の範囲で、調査・仕様案・実装・検証・自己レビュー・文書化・報告を一貫して担当する。
- レビュー、修正、テストの各工程で承認を取り直さない。安全で可逆な実装上の判断は、仮定を明記して進める。目的や利用者への約束が変わる選択は、推奨案と比較材料を用意して人間に判断を求める。
- 着手前に現在のブランチ・差分・関連仕様を確認する。mainへ直接コミットせず、専用の `codex/` ブランチまたはworktreeで作業し、他の作業の変更を混ぜない。
- 現行仕様を基準とし、廃止済み構成を独断で復元しない。依頼外の新機能や大規模な整理は、候補として報告する。

### 個別承認なしで進める範囲

- 読み取り調査、レビュー、影響分析、仕様・Issue・告知の案、受け入れ条件の作成。
- 依頼範囲のコード・ドキュメント修正、マイグレーションファイル作成、関連テスト・Lint・静的解析・自己レビュー・指摘修正。
- 実データから隔離された使い捨てテストDBの作成・マイグレーション・テストデータ操作。
- 開発依頼に伴う作業ブランチへのコミット、既存の対象リポジトリへの通常のpush、Draft PR作成・更新。pushやPR作成が本番反映などを起動しないことを事前に確認する。force pushや他人の変更の破棄は含まない。
- 既に承認された対象・操作・範囲について、重複する承認を求めない。承認対象が変わった場合は変更点を示す。
- 修正ごとに関連する検証と自己レビューを完了し、修正単位で作業ブランチへコミットして通常のpushを行う。検証失敗やpush失敗は明示し、未完了の修正や無関係な変更を混ぜない。上記の本番反映を起動しないことの確認と承認境界は引き続き守る。

### 人間の承認が必要な境界

- mainへのマージ、本番デプロイ、本番ロールバック。
- 共有開発環境・本番環境へのDBマイグレーション適用、実ユーザーデータの変更・削除。ローカルでも実データを含むDBは同様に扱う。
- Secrets・APIキー・IAM・OAuth・アクセス権限の変更、AWSリソースの作成・削除、契約・課金・返金、継続費用の増加。
- 外部ユーザーへのメール・LINE・正式な通知の送信。料金・規約・保存期間・補償・公開日・機能廃止などの決定と公表。
- 承認前に、可能な調査・実装・検証・文案作成を済ませ、対象、具体的な操作、影響、検証結果、未確認事項、復旧方法を提示する。承認待ちの操作以外は進める。

### ステージング反映の条件

- `aws-pre` / `stg.tableno.jp` は共有の稼働環境として扱う。対象環境と反映範囲がユーザーの依頼または既存の承認に含まれ、必要なチェックに合格し、対象コミット・現在の稼働版・復旧手順が確認できた場合に実行する。
- DB変更・実データ変更・権限変更・リソース作成削除・継続費用増加を伴う場合は、それぞれの承認も確認する。通常のアプリ反映に必要な既存ECSサービスのイメージ更新・タスク定義リビジョン登録は、承認済みデプロイの範囲に含む。
- 詳細な実施・検証手順は `iaia-aws-dev-deploy` スキルに従う。検証失敗を成功扱いせず、追加の影響を伴う操作を止めて原因と復旧案を報告する。

### 検証・完了報告

- 実装変更は既存の品質基準と該当ガイドラインに従い、変更に必要なテストとチェックを実行する。文書だけの変更は差分・記述・リンクを確認し、アプリの全体テストは原則不要とする。
- テスト失敗・未実施・CI待ちを明示し、Draft PRの作成と、検証完了・マージ可能・リリース完了を区別する。
- 人間がコードを逐行確認しなくても判断できるよう、変更内容と理由、利用者への影響、変更ファイル、検証結果、未確認事項、復旧方法を報告する。UI変更には必要に応じて画面や代表操作の確認結果を添える。
- DB・セキュリティ・費用への影響を示す。影響がない項目はまとめて記載し、推測を確認済み事実として報告しない。認証・決済・権限・秘匿情報・個人情報・削除処理は重点的にレビューする。
- 権限不足、認証切れ、必須チェック失敗、対象の不一致などで完遂できない場合は、完了した範囲と残作業、必要な判断を具体的に示す。

### 運用ルールと設定の区別

- この文書は作業方針であり、実行環境のサンドボックス・承認設定やGitHubのブランチ保護を変更するものではない。実行環境やツールの制約は引き続き守る。
- 定期巡回は、ユーザーが依頼した際に対象・頻度・実行範囲を定めて設定する。この文書の追加だけで定期実行を開始しない。

## 📁 ガイドライン体系

詳細なガイドラインは用途別に整理されています。作業内容に応じて適切なガイドラインを参照してください。

### 🔍 作業別ガイドライン参照

| 作業内容 | 参照ガイドライン |
|---------|-----------------|
| **新機能開発** | 1. [課題管理](docs/guidelines/ISSUE_MANAGEMENT_GUIDELINES.md)<br>2. [TDD](docs/guidelines/TDD_GUIDELINES.md) |
| **キャラクターシート開発** | 1. [キャラクターシート制限事項](docs/guidelines/CHARACTER_SHEET_GUIDELINES.md)<br>2. [機能一覧](docs/character_sheet/CHARACTER_SHEET_FEATURES.md) - 実装済み機能の詳細<br>3. [技能タブ仕様](docs/character_sheet/SKILL_TAB_SPECIFICATION.md) - 技能タブUI仕様<br>4. [一覧画面仕様](docs/specifications/CHARACTER_LIST_SPECIFICATION.md) - キャラクター一覧画面の仕様 |
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
python3 scripts/dev/create_admin.py  # パスワードは実行時に表示されます

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

- **Backend**: Django 5.2系（`requirements.txt` は `>=5.2,<5.3`）, Django REST Framework
- **Database**: SQLite (開発), PostgreSQL (本番推奨)
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Testing**: pytest, Selenium, Playwright
- **Authentication**: django-allauth (Google/X OAuth) + Django REST Framework (API経由)

## 📋 重要な制限事項

### キャラクターシート機能
- **対応システム**: クトゥルフ神話TRPG 6版・7版のみ
- **7版開発**: 正式サポート対象（`docs/character_sheet/CHARACTER_SHEET_7TH_EDITION_SPECIFICATION.md` を参照）
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
- [キャラクター一覧画面仕様書](docs/specifications/CHARACTER_LIST_SPECIFICATION.md)
- [プロジェクト仕様書](docs/specifications/PROJECT_SPECIFICATION.md)

### 管理ファイル
- [課題管理](docs/archive/issues.md) - 現在の課題と優先順位
- [完了課題](docs/archive/issues_closed.md) - 完了済み課題のアーカイブ

### テスト関連
- [Seleniumインストールガイド](docs/testing/SELENIUM_INSTALLATION_GUIDE.md)
- [E2Eテストセットアップ](docs/testing/E2E_TEST_SETUP.md)
- [UIテストケース・結果](docs/test_results/ui/README.md) - キャラクター作成画面のテストドキュメント

## 🌐 環境情報

### 現在の環境
- Working directory: /mnt/c/Users/endke/Workspace/iaia
- Platform: Linux (WSL2)
- Git branch: main

### テスト済み環境
- Python: 3.11+
- Django: 5.2系（`requirements.txt` は `>=5.2,<5.3`）
- Node.js: 20+ (Playwright用)
- Chromium: 138.0.7204.49
