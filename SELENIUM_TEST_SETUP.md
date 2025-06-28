# Selenium UI テスト環境セットアップ

## 概要
このドキュメントは、Arkham Nexus プロジェクトでSelenium UIテストを実行するための環境セットアップ手順を説明します。

## インストール済み環境（2025年6月27日時点）

### ブラウザ
- **Chromium**: 138.0.7204.49 snap
- **ChromeDriver**: 1:85.0.4183.83-0ubuntu2.22.04.1

### Pythonパッケージ
- **selenium**: 4.33.0
- **webdriver-manager**: 4.0.2

### WSL GUI サポートライブラリ
以下のライブラリがインストール済みです：
- fonts-noto-cjk (日本語フォント)
- libatk-bridge2.0-0
- libcairo2
- libdrm2
- libgbm1
- libglib2.0-0
- libnss3
- libpango-1.0-0
- libxcomposite1
- libxdamage1
- libxkbcommon0
- libxrandr2

## セットアップ手順（新規環境の場合）

### 1. Pythonパッケージのインストール
```bash
pip install selenium webdriver-manager
```

### 2. Chromiumのインストール（Ubuntu/WSL）
```bash
# パッケージリストの更新
sudo apt update

# Chromiumとドライバーのインストール
sudo apt install -y chromium-browser chromium-chromedriver

# WSL GUI サポートライブラリのインストール
sudo apt install -y \
    fonts-noto-cjk \
    libatk-bridge2.0-0 \
    libcairo2 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnss3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxkbcommon0 \
    libxrandr2
```

### 3. インストール確認
```bash
# Chromiumのバージョン確認
chromium --version

# ヘッドレスモードの動作確認
chromium --headless --disable-gpu --dump-dom https://www.google.com
```

## テストの実行

### 全UIテストの実行
```bash
python3 manage.py test tests.ui.test_character_6th_ui -v 2
```

### 特定のテストクラスの実行
```bash
# Seleniumを使用しないテスト
python3 manage.py test tests.ui.test_character_6th_ui.Character6thTemplateRenderingTest

# Seleniumを使用するテスト（ブラウザが必要）
python3 manage.py test tests.ui.test_character_6th_ui.Character6thJavaScriptTest
```

### 簡易UIテストの実行（Selenium不要）
```bash
python3 manage.py test tests.ui.test_character_6th_ui_simple -v 2
```

## トラブルシューティング

### snapでインストールされたChromiumの場合
Chromiumがsnapパッケージとしてインストールされている場合、パスが通常と異なることがあります。
テストコードは自動的にChromiumを検出しますが、問題が発生した場合は以下を確認してください：

```bash
# Chromiumの実行パスを確認
which chromium
# 通常: /snap/bin/chromium

# ChromeDriverのパスを確認
which chromedriver
```

### ヘッドレスモードでのエラー
WSL環境では、以下のオプションを使用することを推奨します：
- `--headless`: GUIなしで実行
- `--no-sandbox`: サンドボックスを無効化（WSL環境で必要）
- `--disable-dev-shm-usage`: /dev/shmの使用を無効化
- `--disable-gpu`: GPU アクセラレーションを無効化

### 日本語文字化け
日本語フォントがインストールされていることを確認してください：
```bash
# フォントの確認
fc-list | grep -i noto | grep -i cjk

# インストールされていない場合
sudo apt install -y fonts-noto-cjk
```

## 関連ファイル

- `/tests/ui/test_character_6th_ui.py`: Selenium UIテスト（フル機能）
- `/tests/ui/test_character_6th_ui_simple.py`: 簡易UIテスト（Selenium不要）
- `/run_character_6th_tests.py`: 全テスト実行スクリプト
- `/CLAUDE.md`: 環境設定の詳細情報