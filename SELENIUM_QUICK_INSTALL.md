# Selenium クイックインストールガイド

## 🚀 5分でSelenium環境を構築

### 1. 必要なものを一括インストール（Ubuntu/WSL）

```bash
# システムを更新
sudo apt update

# Chromium と必要なライブラリを一括インストール
sudo apt install -y \
    chromium-browser \
    chromium-chromedriver \
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

# Python パッケージをインストール
pip install selenium==4.33.0 webdriver-manager==4.0.2
```

### 2. 動作確認（30秒テスト）

```python
# test_selenium.py として保存
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# オプション設定
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# snap chromium の場合
import os
if os.path.exists('/snap/bin/chromium'):
    options.binary_location = '/snap/bin/chromium'

# テスト実行
driver = webdriver.Chrome(options=options)
driver.get('https://www.google.com')
print(f"✅ Success! Title: {driver.title}")
driver.quit()
```

実行:
```bash
python3 test_selenium.py
```

### 3. プロジェクトでのテスト実行

```bash
# タブレノ の UI テストを実行
python3 manage.py test tests.ui.test_character_6th_ui_simple -v 2
```

## ❌ よくあるエラーと解決法

### エラー1: "chromedriver not found"
```bash
# 解決法
sudo apt install chromium-chromedriver
```

### エラー2: "Chrome binary not found"
```bash
# 解決法（snap版の場合）
export CHROME_BIN=/snap/bin/chromium
```

### エラー3: セッション競合
```bash
# 解決法
pkill -f chrome
pkill -f chromium
```

## 📝 最小限の設定ファイル

`conftest.py` をテストディレクトリに作成:
```python
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

@pytest.fixture
def chrome_options():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return options

@pytest.fixture
def driver(chrome_options):
    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    driver.quit()
```

## ✅ インストール完了チェックリスト

- [ ] `chromium --version` でバージョンが表示される
- [ ] `pip show selenium` で 4.33.0 以上が表示される
- [ ] 上記のテストスクリプトが正常に実行される
- [ ] プロジェクトの UI テストが実行できる

---

詳細な設定やトラブルシューティングは [SELENIUM_INSTALLATION_GUIDE.md](./docs/SELENIUM_INSTALLATION_GUIDE.md) を参照してください。