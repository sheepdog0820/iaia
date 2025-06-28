#!/bin/bash
# WSL Ubuntu で Chrome/Chromium をインストールするスクリプト

echo "Chrome/Chromium インストールスクリプト"
echo "======================================"
echo ""
echo "このスクリプトを実行するには sudo 権限が必要です。"
echo ""
echo "オプション1: Google Chrome をインストール"
echo "オプション2: Chromium をインストール（推奨）"
echo ""
read -p "どちらをインストールしますか? (1/2): " choice

if [ "$choice" = "1" ]; then
    echo "Google Chrome をインストールします..."
    
    # 署名キーを追加
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    
    # リポジトリを追加
    sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
    
    # パッケージリストを更新
    sudo apt update
    
    # Google Chrome をインストール
    sudo apt install -y google-chrome-stable
    
    # バージョン確認
    echo ""
    echo "インストール完了！"
    google-chrome --version
    
elif [ "$choice" = "2" ]; then
    echo "Chromium をインストールします..."
    
    # パッケージリストを更新
    sudo apt update
    
    # Chromium と ChromeDriver をインストール
    sudo apt install -y chromium-browser chromium-chromedriver
    
    # バージョン確認
    echo ""
    echo "インストール完了！"
    chromium-browser --version
    chromedriver --version
    
else
    echo "無効な選択です。スクリプトを終了します。"
    exit 1
fi

echo ""
echo "ヘッドレスモードのテスト..."
if [ "$choice" = "1" ]; then
    google-chrome --headless --disable-gpu --dump-dom https://www.google.com | head -10
else
    chromium-browser --headless --disable-gpu --dump-dom https://www.google.com | head -10
fi

echo ""
echo "インストールが完了しました！"
echo "Selenium テストを実行できるようになりました。"