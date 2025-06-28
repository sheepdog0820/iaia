# E2Eテスト環境セットアップガイド

## WSL環境でのPlaywright設定

### 方法1: WSL内で依存関係をインストール（推奨）

WSL内でブラウザを実行するために必要な依存関係をインストールします。

```bash
# 1. システムパッケージを更新
sudo apt-get update

# 2. Playwrightが推奨する依存関係を自動インストール
sudo npx playwright install-deps

# または、手動で必要なパッケージをインストール
sudo apt-get install -y \
    libnspr4 \
    libnss3 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2

# 3. 日本語フォントのインストール（日本語表示が必要な場合）
sudo apt-get install -y fonts-noto-cjk

# 4. ブラウザを再インストール
npx playwright install
```

### 方法2: Windows側でテストを実行

WSL内のサーバーにWindows側からアクセスする方法です。

#### Windows PowerShellまたはコマンドプロンプトで実行:

```powershell
# 1. プロジェクトディレクトリに移動
cd C:\Users\endke\Workspace\iaia

# 2. Node.jsがインストールされていない場合はインストール
# https://nodejs.org/ からダウンロード

# 3. 依存関係をインストール
npm install

# 4. Playwrightブラウザをインストール
npx playwright install

# 5. WSL内のサーバーにアクセスするよう設定を変更
# playwright.config.tsのbaseURLを以下に変更:
# baseURL: 'http://localhost:8000'

# 6. E2Eテストを実行
npm run test:e2e
```

### 方法3: Docker環境でテストを実行

Dockerを使用して一貫した環境でテストを実行します。

```dockerfile
# Dockerfile.e2e
FROM mcr.microsoft.com/playwright:v1.53.0-jammy

WORKDIR /app

# 依存関係のコピーとインストール
COPY package*.json ./
RUN npm ci

# アプリケーションコードのコピー
COPY . .

# テスト実行
CMD ["npm", "run", "test:e2e"]
```

```bash
# Docker imageをビルド
docker build -f Dockerfile.e2e -t e2e-tests .

# テストを実行
docker run --rm --network="host" e2e-tests
```

### 方法4: WSL2でGUI表示を有効化（高度な設定）

WSL2でGUIアプリケーションを表示できるようにする設定です。

```bash
# 1. WSLgがインストールされているか確認（Windows 11または最新のWindows 10）
wsl --version

# 2. X11転送の設定（古いWindows 10の場合）
# Windows側でVcXsrvやXmingなどのXサーバーをインストール

# 3. 環境変数の設定
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0

# 4. ~/.bashrcに追加
echo 'export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '\''{print $2}'\''):0' >> ~/.bashrc

# 5. ヘッドフルモードでテスト実行
npm run test:e2e:headed
```

## トラブルシューティング

### 問題1: "Cannot find module '@playwright/test'"

```bash
# node_modulesを削除して再インストール
rm -rf node_modules package-lock.json
npm install
```

### 問題2: ブラウザが起動しない

```bash
# Playwrightのデバッグモードで実行
DEBUG=pw:api npm run test:e2e

# または、Playwrightのインストール状態を確認
npx playwright --version
npx playwright show-browsers
```

### 問題3: タイムアウトエラー

```typescript
// playwright.config.tsでタイムアウトを延長
export default defineConfig({
  timeout: 60000, // 60秒
  expect: {
    timeout: 10000 // 10秒
  },
  // ...
});
```

### 問題4: WSL1の場合

WSL1ではブラウザの実行が困難なため、WSL2へのアップグレードを推奨します。

```powershell
# Windows PowerShell（管理者権限）で実行
wsl --set-version Ubuntu 2
```

## 推奨環境

- **開発環境**: 方法1（WSL内で依存関係インストール）
- **CI/CD環境**: 方法3（Docker）
- **デバッグ時**: 方法2（Windows側で実行）または方法4（GUI有効化）

## テスト実行コマンド

環境設定後、以下のコマンドでテストを実行できます：

```bash
# 全E2Eテスト実行
npm run test:e2e

# UIモードで実行（インタラクティブ）
npm run test:e2e:ui

# 特定のテストファイルのみ実行
npx playwright test tests/e2e/character.spec.ts

# ブラウザを表示して実行
npm run test:e2e:headed

# デバッグモードで実行
npm run test:e2e:debug

# テストレポートを表示
npm run test:e2e:report
```

## 注意事項

1. **メモリ使用量**: ブラウザテストは多くのメモリを使用します。WSLのメモリ割り当てを増やすことを推奨します。

2. **ネットワーク設定**: WSL2とWindowsホスト間のネットワーク通信が正しく設定されていることを確認してください。

3. **ファイアウォール**: Windows DefenderファイアウォールがWSLからのアクセスをブロックしていないか確認してください。

4. **パフォーマンス**: WSL内でのブラウザ実行は、ネイティブ環境より遅い場合があります。