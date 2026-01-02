# Selenium インストールガイド

## 概要
このドキュメントは、タブレノ プロジェクトでSelenium UIテストを実行するための環境構築手順を説明します。

## 必要なコンポーネント

### 1. Python パッケージ
- selenium >= 4.33.0
- webdriver-manager >= 4.0.2

### 2. ブラウザ
- Google Chrome または Chromium
- ChromeDriver（ブラウザに対応するバージョン）

### 3. システムライブラリ（WSL/Linux）
- GUI サポートライブラリ
- 日本語フォント

## インストール手順

### Step 1: Python パッケージのインストール

```bash
# 仮想環境の有効化（プロジェクトルートで実行）
source venv/bin/activate  # Windows: venv\Scripts\activate

# Selenium関連パッケージのインストール
pip install selenium==4.33.0
pip install webdriver-manager==4.0.2

# または requirements.txt から一括インストール
pip install -r requirements.txt
```

### Step 2: ブラウザのインストール

#### オプション A: Chromium のインストール（推奨）

```bash
# Ubuntu/Debian/WSL
sudo apt update
sudo apt install -y chromium-browser chromium-chromedriver

# バージョン確認
chromium --version
chromedriver --version
```

#### オプション B: Google Chrome のインストール

```bash
# 1. Google の署名キーを追加
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -

# 2. リポジトリを追加
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'

# 3. パッケージリストを更新
sudo apt update

# 4. Google Chrome をインストール
sudo apt install -y google-chrome-stable

# 5. バージョン確認
google-chrome --version
```

### Step 3: WSL/Linux 用の依存ライブラリ

```bash
# GUI サポートライブラリと日本語フォントのインストール
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

### Step 4: ChromeDriver の設定

#### 自動管理（webdriver-manager 使用）
```python
# テストコード内で自動的にドライバーをダウンロード
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
```

#### 手動インストール
```bash
# ChromeDriver のダウンロード（バージョンは Chrome に合わせる）
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$(google-chrome --version | cut -d' ' -f3 | cut -d'.' -f1)/chromedriver_linux64.zip

# 解凍
unzip chromedriver_linux64.zip

# 実行権限を付与して適切な場所に配置
chmod +x chromedriver
sudo mv chromedriver /usr/local/bin/
```

## 動作確認

### 基本的な動作確認
```bash
# Python インタープリタで確認
python3
```

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ヘッドレスモードの設定
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# ドライバーの起動
driver = webdriver.Chrome(options=options)

# Google にアクセス
driver.get('https://www.google.com')
print(driver.title)

# ブラウザを閉じる
driver.quit()
```

### プロジェクトのテスト実行
```bash
# Selenium UIテストの実行
python3 manage.py test tests.ui.test_character_6th_ui -v 2

# 簡易UIテスト（Selenium不要）の実行
python3 manage.py test tests.ui.test_character_6th_ui_simple -v 2
```

## トラブルシューティング

### 1. "chromedriver not found" エラー
```bash
# ChromeDriver のパスを確認
which chromedriver

# パスが見つからない場合は環境変数に追加
export PATH=$PATH:/usr/local/bin
```

### 2. "Chrome binary not found" エラー
```bash
# Chrome/Chromium の実行パスを確認
which chromium-browser || which google-chrome

# テストコードで明示的にパスを指定
options.binary_location = '/usr/bin/chromium-browser'
```

### 3. WSL でのディスプレイエラー
```bash
# WSLg が有効になっているか確認
echo $DISPLAY

# ヘッドレスモードを使用
options.add_argument('--headless')
```

### 4. snap でインストールされた Chromium の問題
```bash
# snap chromium の場合、特別な設定が必要
# テストコードで以下のように設定
import os

if os.path.exists('/snap/bin/chromium'):
    options.binary_location = '/snap/bin/chromium'
```

### 5. セッション競合エラー
```bash
# 既存の Chrome プロセスを終了
pkill -f chrome
pkill -f chromium

# ユーザーデータディレクトリを指定
options.add_argument('--user-data-dir=/tmp/test-profile')
```

## 環境別の注意事項

### WSL2 環境
- WSLg (GUI サポート) が有効になっていることを確認
- Windows 11 または Windows 10 (ビルド 19044以降) が必要
- ヘッドレスモードの使用を推奨

### Docker 環境
```dockerfile
# Dockerfile の例
FROM python:3.11

# Chrome の依存関係
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Python パッケージ
RUN pip install selenium webdriver-manager
```

### CI/CD 環境
```yaml
# GitHub Actions の例
- name: Setup Chrome
  uses: browser-actions/setup-chrome@latest
- name: Run UI tests
  run: |
    pip install selenium webdriver-manager
    python manage.py test tests.ui
```

## 推奨設定

### テスト用の Chrome オプション
```python
def get_chrome_options():
    """テスト用の推奨 Chrome オプション"""
    options = Options()
    
    # ヘッドレスモード
    options.add_argument('--headless')
    
    # セキュリティ関連
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # パフォーマンス
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    
    # ウィンドウサイズ
    options.add_argument('--window-size=1920,1080')
    
    # その他
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    
    return options
```

## 関連ドキュメント
- [SELENIUM_TEST_SETUP.md](./SELENIUM_TEST_SETUP.md) - テスト環境セットアップの詳細
- [requirements.txt](../requirements.txt) - プロジェクトの依存関係
- [tests/ui/](../tests/ui/) - UIテストのソースコード

## 更新履歴
- 2025-06-27: 初版作成（WSL Ubuntu 環境での設定を含む）